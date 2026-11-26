#!/usr/bin/env python3
"""Register-definition driven decoding for CATC traces (framework only, no vendor values).

A regdef JSON file is supplied by an engineer and says what each bit of a register
means. This module (1) validates it, (2) decodes observed config accesses offline
(annotate) and (3) emits an experimental CATC .dec script (emit-dec).
Nothing here defines vendor registers: a definition without provenance is rejected,
bytes not covered by byte enables stay UNKNOWN, and bits the definition does not
name are never decoded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = 'pcie.catc-regdef/v1'
OUT_SCHEMA = 'pcie.catc-decoded-accesses/v1'
TOP_KEYS = {'schema', 'name', 'space', 'match', 'provenance', 'registers'}
PROV_KEYS = ('source', 'who', 'date')
ACCESS = {'RO', 'RW', 'RW1C', 'RWS', 'RW1CS', 'ROS', 'HWINIT', 'RSVDP', 'RSVDZ', 'UNDEFINED'}
NAME_RE = re.compile(r'^[A-Za-z0-9_ ./\[\]:()+-]{1,64}$')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def _int(value, what):
    if isinstance(value, bool):
        raise ValueError(f'{what} must be an integer')
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            pass
    raise ValueError(f'{what} must be an integer or 0x string')


def load(path):
    """Read and validate a regdef; returns a normalised dict with integer fields."""
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    return validate(raw)


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError('regdef must be an object')
    if raw.get('schema') != SCHEMA:
        raise ValueError(f'schema must be {SCHEMA}')
    extra = set(raw) - TOP_KEYS
    if extra:
        raise ValueError(f'unknown top-level keys: {sorted(extra)}')
    if raw.get('space') not in ('cfg', 'mem'):
        raise ValueError('space must be cfg or mem')
    prov = raw.get('provenance')
    if not isinstance(prov, dict) or any(not str(prov.get(k, '')).strip() for k in PROV_KEYS):
        raise ValueError('provenance needs non-empty source, who, date (definitions are not guessed)')
    if prov.get('permitted_for_tool_use') is not True:
        raise ValueError('provenance.permitted_for_tool_use must be true (owner/engineer allowed this source)')
    match = raw.get('match') or {}
    bar_base = None
    if raw['space'] == 'mem':
        if match.get('bar_base') is None:
            raise ValueError('mem space needs match.bar_base (address of the register block)')
        bar_base = _int(match['bar_base'], 'match.bar_base')
        if not 0 <= bar_base < 1 << 32:
            raise ValueError('match.bar_base must fit 32 bits (64-bit addresses not supported yet)')
    registers, seen_bytes = [], set()
    if not isinstance(raw.get('registers'), list):
        raise ValueError('registers must be a list')
    for r in raw['registers']:
        name = r.get('name', '')
        if not NAME_RE.match(str(name)):
            raise ValueError(f'invalid register name {name!r}')
        offset = _int(r.get('offset'), f'{name}.offset')
        width = _int(r.get('width_bits', 32), f'{name}.width_bits')
        if width not in (8, 16, 32):
            raise ValueError(f'{name}: width_bits must be 8, 16 or 32')
        if offset < 0 or offset % (width // 8) or offset + width // 8 > 1 << 32:
            raise ValueError(f'{name}: offset 0x{offset:X} not aligned to {width} bits')
        if any(x['name'] == name for x in registers):
            raise ValueError(f'duplicate register name {name!r}')
        span = set(range(offset, offset + width // 8))
        if span & seen_bytes:
            raise ValueError(f'{name}: overlaps another register')
        seen_bytes |= span
        fields, used = [], 0
        for f in r.get('fields', []):
            fname = f.get('name', '')
            if not NAME_RE.match(str(fname)):
                raise ValueError(f'{name}: invalid field name {fname!r}')
            if any(x['name'] == fname for x in fields):
                raise ValueError(f'{name}: duplicate field name {fname!r}')
            lsb, fw = _int(f.get('lsb'), f'{fname}.lsb'), _int(f.get('width'), f'{fname}.width')
            if lsb < 0 or fw < 1 or lsb + fw > width:
                raise ValueError(f'{name}.{fname}: bits [{lsb + fw - 1}:{lsb}] outside {width}-bit register')
            mask = ((1 << fw) - 1) << lsb
            if used & mask:
                raise ValueError(f'{name}.{fname}: overlaps another field')
            used |= mask
            access = f.get('access', 'UNDEFINED')
            if access not in ACCESS:
                raise ValueError(f'{name}.{fname}: access {access!r} not one of {sorted(ACCESS)}')
            values = {}
            for k, label in (f.get('values') or {}).items():
                key = _int(k, f'{fname}.values key')
                if not 0 <= key < 1 << fw:
                    raise ValueError(f'{name}.{fname}: value {key} does not fit {fw} bits')
                if not str(label).strip():
                    raise ValueError(f'{name}.{fname}: empty label for {key}')
                values[key] = str(label)
            fields.append({'name': fname, 'lsb': lsb, 'width': fw, 'access': access,
                           'description': str(f.get('description', '')), 'values': values})
        registers.append({'name': name, 'offset': offset, 'width_bits': width, 'fields': fields})
    return {'schema': SCHEMA, 'name': str(raw.get('name', '')), 'space': raw['space'],
            'bar_base': bar_base, 'provenance': prov, 'registers': registers}


def decode_known(regdef, offset, value, known_mask):
    """Decode one DWORD-aligned value whose valid bits are given by known_mask (32-bit, bit n set = bit n known).

    A field is decoded only when all of its bits are known; otherwise it is UNKNOWN and no value is invented.
    Bits outside known_mask never influence a decoded field.
    """
    if offset % 4 or not 0 <= value < 1 << 32 or not 0 <= known_mask < 1 << 32:
        raise ValueError('offset must be DWORD aligned, value and known_mask 32-bit')
    out = []
    for reg in regdef['registers']:
        base = reg['offset'] - offset
        if not 0 <= base < 4:
            continue
        fields = []
        for f in reg['fields']:
            lo = base * 8 + f['lsb']
            field_mask = (1 << f['width']) - 1
            if (known_mask >> lo) & field_mask != field_mask:
                fields.append({'field': f['name'], 'lsb': f['lsb'], 'width': f['width'],
                               'value': None, 'label': None, 'status': 'UNKNOWN_BITS_NOT_KNOWN'})
                continue
            v = value >> lo & field_mask
            label = f['values'].get(v)
            fields.append({'field': f['name'], 'lsb': f['lsb'], 'width': f['width'], 'value': v,
                           'label': label, 'status': 'DECODED' if label else 'VALUE_NOT_DEFINED'})
        out.append({'register': reg['name'], 'offset': reg['offset'], 'fields': fields})
    return out


def decode_value(regdef, offset, value, byte_enable=0xF):
    """Decode one DWORD-aligned access.

    byte_enable: 4-bit mask, bit n set means payload byte n is valid. A field that touches any
    disabled byte is reported UNKNOWN_BYTES_NOT_ENABLED, never as zero.
    """
    if not 0 <= byte_enable <= 0xF:
        raise ValueError('offset must be DWORD aligned, value 32-bit, byte_enable 4-bit')
    known = sum(0xFF << 8 * i for i in range(4) if byte_enable >> i & 1)
    out = decode_known(regdef, offset, value, known)
    for reg in out:
        for f in reg['fields']:
            if f['status'] == 'UNKNOWN_BITS_NOT_KNOWN':
                f['status'] = 'UNKNOWN_BYTES_NOT_ENABLED'
    return out


def annotate(log, regdef, device_id, epoch=None):
    """Decode config accesses of a B2b access log (cfg space only)."""
    if regdef['space'] != 'cfg':
        raise ValueError('annotate supports cfg regdefs only (memory accesses are not in the B2b log)')
    rows, skipped = [], {'no_value': 0, 'unaligned_offset': 0}
    for a in log['accesses']:
        if a['device_id'] != device_id or (epoch is not None and a['epoch'] != epoch):
            continue
        is_write = a['type'].startswith('CfgWr')
        value = a['write_value'] if is_write else a['read_value']
        if value is None:
            skipped['no_value'] += 1
            continue
        if a['register_byte_offset'] % 4:
            skipped['unaligned_offset'] += 1
            continue
        be = a['first_be'] if a['first_be'] is not None else 0xF
        decoded = decode_value(regdef, a['register_byte_offset'], value, be)
        if not decoded:
            continue
        rows.append({'access_id': a['access_id'], 'packet_index': a['packet_index'], 'time_display': a['time_display'],
                     'type': a['type'], 'epoch': a['epoch'], 'byte_offset': a['register_byte_offset'],
                     'first_be': be, 'value_kind': 'WRITE_INTENT' if is_write else 'READ_RETURN',
                     'raw_value': value, 'registers': decoded})
    return {'schema': OUT_SCHEMA, 'regdef': {'name': regdef['name'], 'provenance': regdef['provenance']},
            'device_id': device_id, 'epoch_filter': epoch, 'rows': rows, 'skipped_accesses': skipped,
            'not_established': ['write rows are intent, not applied hardware state',
                                'bits not named in the definition are not decoded',
                                'definition correctness rests on its stated provenance']}


def render_markdown(doc):
    lines = [f"# Decoded accesses: {doc['regdef']['name']}", '',
             f"Source: {doc['regdef']['provenance']['source']} ({doc['regdef']['provenance']['who']}, {doc['regdef']['provenance']['date']}).",
             'Write rows are write intent, not applied state. Unnamed bits are not decoded.', '',
             '| Packet | Time | Type | Kind | Register | Raw | Field | Value | Meaning |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['rows']:
        for reg in r['registers']:
            for f in reg['fields']:
                val = 'UNKNOWN' if f['value'] is None else f"{f['value']} (0x{f['value']:X})"
                meaning = f['label'] or f['status']
                lines.append(f"| {r['packet_index']} | {r['time_display']} | {r['type']} | {r['value_kind']} | {reg['register']} | 0x{r['raw_value']:X} | {f['field']}[{f['lsb'] + f['width'] - 1}:{f['lsb']}] | {val} | {meaning} |")
    return '\n'.join(lines) + '\n'


def _csl_str(text):
    return '"' + str(text).replace('\\', '\\\\').replace('"', "'").replace('\n', ' ') + '"'


def emit_dec(regdef, source_sha):
    """Emit an experimental CATC file-based decoder. Inactive until the user removes the underscores.

    Observed in PETracer 13.26 (docs/pcie-catc-decode-verification.md): in.Data of a write is the
    DWORD as a big-endian bit stream, so register bit n sits at stream offset 31 - n; a read request
    carries no data (in.DataLength 0), so reads are not decoded here.
    """
    cfg = regdef['space'] == 'cfg'
    out_type = '__CFG' if cfg else '__MEM'
    key = 'in.Register' if cfg else '(in.AddressLo - 0x%X)' % regdef['bar_base']
    lines = [
        f"# GENERATED by catc_regdef.py from regdef {regdef['name']!r} (sha256 {source_sha}).",
        '# STATUS: see docs/pcie-catc-decode-verification.md for what has been verified in PETracer.',
        f"# Definition source: {regdef['provenance']['source']} / {regdef['provenance']['who']} / {regdef['provenance']['date']}",
        '# Limits: writes of one DWORD only (reads carry no data in the request packet); unnamed bits are not decoded;',
        '# byte enables are checked as one contiguous range (in.FirstByteEnabled, in.EnabledByteCount).',
        '# While active this script replaces CATC standard decoding; other DWORD writes show a raw Data cell.',
        '',
        f'set OutputType = "{out_type}"; # remove the leading underscores to activate',
        '%include "CATCScriptAPI.inc"',
        'const VRD_ViewAll = 1;',
        'const VRD_HideAll = 0;',
        '',
        'ShowVendorRegister()',
        '{',
        '    UnitDecoderInit( "VRD" );',
        '    FieldColor = RGB(128, 0, 0);',
    ]
    by_dword = {}
    for reg in regdef['registers']:
        by_dword.setdefault(reg['offset'] & ~3, []).append(reg)
    first = True
    for dword, regs in sorted(by_dword.items()):
        lines.append(f"    {'if' if first else 'else if'}( in.DataLength == 4 && {key} == 0x{dword:X} )")
        lines.append('    {')
        for reg in regs:
            shift = (reg['offset'] - dword) * 8
            lines.append(f"        AddCaptionCell( {_csl_str(reg['name'])}, \"0x{reg['offset']:X}\", \"Decoded from the supplied register definition.\", _MONOCOLOR, [_FIXEDWIDTH, 8] );")
            for f in reg['fields']:
                lsb = shift + f['lsb']
                top = f['lsb'] + f['width'] - 1
                lo_byte, hi_byte = lsb // 8, (lsb + f['width'] - 1) // 8
                tip = f"{f['name']} [{top}:{f['lsb']}] {f['access']}. {f['description']}".strip()
                lines.append(f"        if( {lo_byte} >= in.FirstByteEnabled && {hi_byte} < in.FirstByteEnabled + in.EnabledByteCount )")
                lines.append('        {')
                lines.append(f"            v = GetNBits( in.Data, {32 - lsb - f['width']}, {f['width']} );")
                lines.append('            txt = Format( "%d", v );')
                for val, label in sorted(f['values'].items()):
                    lines.append(f"            if( v == {val} ) txt = Format( \"%d\", v ) + \" \" + {_csl_str(label)};")
                lines.append(f"            AddPayLoadCell( {_csl_str(f['name'])}, txt, {_csl_str(tip)} );")
                lines.append('        }')
                lines.append('        else')
                lines.append(f"            AddPayLoadCell( {_csl_str(f['name'])}, \"UNKNOWN (bytes not enabled)\", {_csl_str(tip)} );")
        lines.append('    }')
        first = False
    # An active script replaces CATC's own decoding (observed: Command(0x0400) disappears), so keep the raw value.
    lines += ['    else if( in.DataLength == 4 )',
              '    {',
              '        AddPayLoadCell( "Data", Format( "0x%08X", GetNBits( in.Data, 0, 32 ) ), "Raw DWORD; no definition supplied for this register. CATC standard decoding is replaced while this script is active." );',
              '    }']
    lines += ['}', '',
              'ProcessData()', '{',
              '    CommonDecoderInit();',
              '    CellBlockName = "Vendor Register";',
              '    ShowVendorRegister();',
              '    return Complete();',
              '}', '']
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate');  v.add_argument('regdef', type=Path)
    a = sub.add_parser('annotate')
    a.add_argument('regdef', type=Path); a.add_argument('--log', type=Path, required=True)
    a.add_argument('--device-id', type=lambda x: int(x, 0), required=True); a.add_argument('--epoch')
    a.add_argument('--output-dir', type=Path, required=True)
    e = sub.add_parser('emit-dec')
    e.add_argument('regdef', type=Path); e.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        regdef = load(args.regdef)
        if args.cmd == 'validate':
            print(json.dumps({'registers': len(regdef['registers']), 'fields': sum(len(r['fields']) for r in regdef['registers'])}))
        elif args.cmd == 'annotate':
            if args.output_dir.exists():
                raise ValueError('Refusing existing output')
            log = json.loads(args.log.read_text(encoding='utf-8'))
            doc = annotate(log, regdef, args.device_id, args.epoch)
            doc['input'] = {'regdef_sha256': sha256(args.regdef), 'log_sha256': sha256(args.log)}
            args.output_dir.mkdir(parents=True)
            (args.output_dir / 'decoded-accesses.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            (args.output_dir / 'decoded-accesses.md').write_text(render_markdown(doc), encoding='utf-8', newline='\n')
            print(json.dumps({'rows': len(doc['rows'])}))
        else:
            if args.output.exists():
                raise ValueError('Refusing existing output')
            args.output.write_text(emit_dec(regdef, sha256(args.regdef)), encoding='utf-8', newline='\n')
            print(json.dumps({'output': str(args.output)}))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
