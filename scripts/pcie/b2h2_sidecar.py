#!/usr/bin/env python3
"""Read-only sidecar register decoding next to CATC's own Configuration Space state.

Inputs are saved files only: a com_config_space.py snapshot, the B2b access log and an engineer/regdef
file. Nothing here opens PETracer or touches the install folder. Three views are kept apart and never
promoted into each other:
  catc_merged        what CATC's API returned at the query packet (reads and writes merged per bit)
  last_write_intent  what B2b/B2d recorded as sent in writes (per byte, latest write)
  last_read_back     what B2b/B2d paired as completion data (per byte, latest read)
None of them states the hardware's applied value.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import b2b_config_access as b2b
import b2c_capability_resolution as b2c
import b2d_observed_state as b2d
import catc_regdef as rd

SCHEMA = 'pcie.b2h2-sidecar/v1'
SCOPE_EPOCH = 'before_disconnect'
CONFIG_DWORDS = 1024


class OutOfScope(ValueError):
    pass


def normalize_snapshot(space):
    """COM GetData result -> per-DWORD value and bit-level known mask, validated.

    Observed (PETracer 13.26): the second buffer is a per-bit IsSet mask (a 2-bit field reads mask 3).
    Unknown bits are forced to 0 in `value` so a later decoder cannot depend on them.
    """
    try:
        data, mask = space['GetData']
    except (KeyError, TypeError, ValueError):
        raise ValueError('snapshot has no GetData (data, bytes_set)')
    if len(data) != CONFIG_DWORDS or len(mask) != CONFIG_DWORDS:
        raise ValueError(f'GetData must return {CONFIG_DWORDS} DWORDs for data and mask')
    for v in list(data) + list(mask):
        if type(v) is not int or not 0 <= v <= 0xFFFFFFFF:
            raise ValueError('GetData holds a non 32-bit integer')
    value = [d & m for d, m in zip(data, mask)]
    partial_bytes = sorted({i * 4 + b for i, m in enumerate(mask) for b in range(4) if (m >> 8 * b) & 0xFF not in (0, 0xFF)})
    known_bytes = sum(1 for m in mask for b in range(4) if (m >> 8 * b) & 0xFF == 0xFF)
    return {'value': value, 'known': list(mask), 'known_bytes': known_bytes, 'partial_byte_offsets': partial_bytes}


def native_fields(space):
    """CATC's own decoded fields keyed by (absolute bit, width): entry bytes*8 + register bits + field bits."""
    out = {}
    for entry in space.get('entries', []):
        base = entry.get('GetOffset')
        if not isinstance(base, int):
            continue
        for reg in entry.get('registers', []):
            roff = reg.get('GetOffset')
            if not isinstance(roff, int):
                continue
            for f in reg.get('fields', []):
                fo, fs, fv = f.get('GetFieldOffset'), f.get('GetFieldSize'), f.get('GetFieldValue')
                if not (isinstance(fo, int) and isinstance(fs, int) and isinstance(fv, list) and len(fv) == 2):
                    continue
                known = fv[1] & (1 << fs) - 1 == (1 << fs) - 1
                out.setdefault((base * 8 + roff + fo, fs), {'name': f.get('GetFieldName'), 'register': reg.get('GetName'),
                                                            'value': fv[0] if known else None, 'known': known})
    return out


def _dword_view(byte_map, offset):
    """Bytes {offset: {'value', ...}} -> (value, known mask, evidence packets) for one DWORD."""
    value = known = 0
    packets = set()
    for b in range(4):
        item = byte_map.get(str(offset + b))
        if item is not None:
            value |= item['value'] << 8 * b
            known |= 0xFF << 8 * b
            packets.add(item.get('completion_packet', item.get('request_packet')))
    return value, known, sorted(packets)


def _fields(regdef, offset, value, known):
    return {(r['register'], f['field']): f for r in rd.decode_known(regdef, offset, value, known) for f in r['fields']}


def check_scope(log, snapshot_run, device_id, packet):
    if log.get('schema') != b2b.SCHEMA:
        raise ValueError('Unsupported access log')
    epoch = b2c.epoch_at(log, packet)
    if epoch != SCOPE_EPOCH:
        raise OutOfScope(f'NOT_VERIFIED_OUT_OF_SCOPE: packet {packet} is in epoch {epoch!r}; only {SCOPE_EPOCH!r} is verified')
    if snapshot_run.get('bdf') != device_id:
        raise OutOfScope(f"NOT_VERIFIED_OUT_OF_SCOPE: snapshot device {snapshot_run.get('bdf')} differs from {device_id}")
    traces = snapshot_run.get('pre') or []
    if not traces or traces[0].get('sha256') != log['trace']['sha256']:
        raise OutOfScope('NOT_VERIFIED_OUT_OF_SCOPE: snapshot trace SHA-256 differs from the access log trace')
    for key in ('identities_unchanged', 'process_exit_ok'):
        if snapshot_run.get(key) is False:
            raise ValueError(f'snapshot run reports {key}=false')
    return epoch


def build(snapshot_run, log, regdef, packet, device_id, hashes=None):
    epoch = check_scope(log, snapshot_run, device_id, packet)
    space = snapshot_run['packets'].get(str(packet))
    if space is None:
        raise ValueError(f'snapshot has no query for packet {packet}')
    snap = normalize_snapshot(space)
    native = native_fields(space)
    state = b2d.build(log, device_id, packet)
    rows = []
    for dword in sorted({r['offset'] & ~3 for r in regdef['registers']}):
        i = dword // 4
        merged = _fields(regdef, dword, snap['value'][i], snap['known'][i])
        w_val, w_known, w_pk = _dword_view(state['write_intent_bytes'], dword)
        r_val, r_known, r_pk = _dword_view(state['read_bytes'], dword)
        writes = _fields(regdef, dword, w_val, w_known)
        reads = _fields(regdef, dword, r_val, r_known)
        for reg in regdef['registers']:
            if reg['offset'] & ~3 != dword:
                continue
            for f in reg['fields']:
                key = (reg['name'], f['name'])
                abs_bit = reg['offset'] * 8 + f['lsb']
                nat = native.get((abs_bit, f['width']))
                m = merged[key]
                if nat is None:
                    diff = 'NATIVE_FIELD_NOT_FOUND' if native else 'NATIVE_NOT_AVAILABLE'
                elif m['value'] is None or nat['value'] is None:
                    diff = 'NOT_COMPARABLE_UNKNOWN'
                else:
                    diff = 'MATCH' if m['value'] == nat['value'] else 'DIFFERS'
                rows.append({'register': reg['name'], 'offset': reg['offset'], 'field': f['name'], 'lsb': f['lsb'], 'width': f['width'],
                             'catc_merged': {k: m[k] for k in ('value', 'label', 'status')},
                             'last_write_intent': {**{k: writes[key][k] for k in ('value', 'label', 'status')}, 'evidence_request_packets': w_pk},
                             'last_read_back': {**{k: reads[key][k] for k in ('value', 'label', 'status')}, 'evidence_completion_packets': r_pk},
                             'native_catc': None if nat is None else {'name': nat['name'], 'register': nat['register'], 'value': nat['value']},
                             'native_comparison': diff})
    return {
        'schema': SCHEMA,
        'binding': {'trace': snapshot_run['pre'][0], 'petracer': snapshot_run.get('petracer', 'NOT_RECORDED'),
                    'bdf': device_id, 'snapshot_position_packet': packet, 'epoch': epoch,
                    'regdef': {'name': regdef['name'], 'provenance': regdef['provenance']}, 'hashes': hashes or {}},
        'snapshot_position_note': 'snapshot_position_packet is where CATC was queried; it is not the packet of the last update of any field',
        'normalization': {'known_bytes': snap['known_bytes'], 'partial_byte_offsets': snap['partial_byte_offsets']},
        'rows': rows,
        'differences': [r for r in rows if r['native_comparison'] == 'DIFFERS'],
        'not_established': [
            'catc_merged combines reads and writes (possibly from different times) and is not a hardware readback',
            'last_write_intent is what was sent, not the applied hardware state',
            'last_read_back is per byte, latest completion data; it can predate later writes',
            'scope: one trace, one device, epoch before_disconnect only; other epochs are refused, not inherited',
            'definition correctness rests on its stated provenance',
        ]}


def _show(v):
    if v['value'] is None:
        return 'UNKNOWN'
    return f"{v['value']}" + (f" ({v['label']})" if v['label'] else ' (no label)')


def render(doc):
    b = doc['binding']
    lines = [f"# Sidecar register view: {b['regdef']['name']}", '',
             f"Trace SHA-256 {b['trace']['sha256']}; PETracer {b['petracer'].get('file_version', 'NOT_RECORDED') if isinstance(b['petracer'], dict) else b['petracer']}; "
             f"device {b['bdf']}; epoch {b['epoch']}; snapshot position packet {b['snapshot_position_packet']}.",
             'The three value columns are different evidence and are not interchangeable. None of them proves the hardware applied the value.', '',
             '| Register | Field | CATC merged | Last write intent | Last read-back | CATC native field | Native vs sidecar |', '| --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['rows']:
        w, rb, n = r['last_write_intent'], r['last_read_back'], r['native_catc']
        lines.append(f"| {r['register']} 0x{r['offset']:X} | {r['field']}[{r['lsb'] + r['width'] - 1}:{r['lsb']}] | {_show(r['catc_merged'])} | "
                     f"{_show(w)} @ {w['evidence_request_packets'] or 'none'} | {_show(rb)} @ {rb['evidence_completion_packets'] or 'none'} | "
                     f"{('%s = %s' % (n['name'], n['value'])) if n else 'n/a'} | {r['native_comparison']} |")
    lines += ['', 'Not established:'] + [f'- {x}' for x in doc['not_established']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, required=True, help='com_config_space.py output (config-space.json)')
    ap.add_argument('--log', type=Path, required=True, help='B2b accesses.json')
    ap.add_argument('--regdef', type=Path, required=True)
    ap.add_argument('--device-id', type=lambda x: int(x, 0), required=True)
    ap.add_argument('--packet', type=int, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.output_dir.exists():
            raise ValueError('Refusing existing output')
        doc = build(json.loads(a.snapshot.read_text(encoding='utf-8')), json.loads(a.log.read_text(encoding='utf-8')),
                    rd.load(a.regdef), a.packet, a.device_id,
                    {'snapshot_sha256': rd.sha256(a.snapshot), 'b2b_log_sha256': rd.sha256(a.log), 'regdef_sha256': rd.sha256(a.regdef)})
        a.output_dir.mkdir(parents=True)
        (a.output_dir / 'sidecar.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        (a.output_dir / 'sidecar.md').write_text(render(doc), encoding='utf-8', newline='\n')
        print(json.dumps({'rows': len(doc['rows']), 'differences': len(doc['differences'])}))
    except OutOfScope as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
