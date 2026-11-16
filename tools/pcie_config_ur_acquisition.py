"""Acquire supplemental PCIe Config and UR observations from a sealed import."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import gc
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import pcie_navigation_probe as probe  # Also provides the scripts/pcie import path.
import b2a_register_fields as b2a
import g2b_associate as g2b
import native_navigation as nav
import pcie_detail_windows as detail
import pcie_disk_index as disk
import pcie_event_coverage as coverage
import pcie_large_io as large
import pcie_phase_evidence as phase
import pcie_resources as resources
import verify_g1a_log as g1a
from pcie_pipeline import CleanupUnknown, supervised_worker


SCHEMA = 'pcie.config-ur-observations/v1'
MAX_RETAINED_ROWS = 8192
MAX_RAW_TLPS = large.DEFAULTS['max_tlp_rows']
MAX_DETAIL_SPAN = 160
MAX_DETAIL_ANCHORS = 256
TIME_LIMIT = 660
VSE_LIMIT = 360
CLOSE_LIMIT = 30
BINDING_KEYS = ('analysis_id', 'source_trace_sha256', 'display_trace_sha256',
                'packet_namespace', 'native_packet_count')
RAW_TYPES = b2a.CFG | {17, 18}
CONFIG_KINDS = {'CfgRd0', 'CfgWr0', 'CfgRd1', 'CfgWr1'}
COMPLETION_KINDS = {'Cpl', 'CplD'}
MEMORY_KINDS = {1: 'MRd32', 4: 'MRd64'}
DIRECTIONS = {'Upstream', 'Downstream'}
NULL_FIELDS = ('time_ns', 'device_id', 'register', 'address', 'length_dw', 'first_be',
               'last_be', 'value', 'payload_bytes', 'byte_count', 'lower_address', 'status')


def reference(kind, file, sha256, line, fields):
    return dict(kind=kind, file=file, sha256=sha256, line=line, fields=list(fields))


def read_binding(binding):
    value = {key: binding[key] for key in BINDING_KEYS}
    source = coverage.identity(value['analysis_id'], value['source_trace_sha256'],
                               value['display_trace_sha256'], None)
    if value['packet_namespace'] != source['packet_namespace']:
        raise ValueError('Supplemental Packet namespace disagrees with the import')
    if type(value['native_packet_count']) is not int or value['native_packet_count'] < 0:
        raise ValueError('Supplemental Packet range is unknown')
    return value


def kind_of(code):
    name = g2b.VENDOR_TLP_TYPES.get(code)
    if name in CONFIG_KINDS:
        return name
    if name in g2b.COMPLETIONS:
        return 'CplD' if name.endswith('D') or name == 'CplDLk' else 'Cpl'
    if code in MEMORY_KINDS:
        return MEMORY_KINDS[code]
    if name in g2b.NON_POSTED_REQUESTS:
        return 'OtherNonPosted'
    return None


def metadata_event(row):
    code = int(row['tlp_type_hex'], 16)
    kind = kind_of(code)
    if kind is None:
        return None
    direction = row['channel'] if row['channel'] in DIRECTIONS else 'UNKNOWN'
    event = dict.fromkeys(NULL_FIELDS)
    event.update(packet_index=row['packet_index'], time_display=row['time_display'] or '',
                 direction=direction, kind=kind, requester_id=row['requester_id'], tag=row['tag'], evidence=[])
    if kind in COMPLETION_KINDS:
        event.update(device_id=row['completer_id'], status=g2b.STATUS_NAMES.get(row['compl_status'], 'UNKNOWN'))
    return event


def validate_import(root, working, binding):
    path = root / 'worker.json'
    receipt = probe.read_json(path)
    if receipt.get('status') not in ('ANALYSIS_COMPLETE', 'NO_TLP_OBSERVED') or receipt.get('cleanup_status') != 'confirmed':
        raise ValueError('Import has no completed and cleaned native receipt')
    if (receipt['before']['source_trace']['sha256'] != binding['source_trace_sha256']
            or receipt['working_after'] != working or receipt.get('working_unchanged') is not True
            or receipt['native_packet_count'] != binding['native_packet_count']):
        raise ValueError('Native import receipt disagrees with the supplemental source')
    if root.parent.name != binding['analysis_id']:
        raise ValueError('Native import belongs to another analysis')
    probes = {p['name']: p for p in receipt['probes']}
    count_path = coverage.bound_log(root, 'count.txt', probes['count'])
    total = g1a.check_log(count_path.read_text(encoding='utf-8'))['tlp_callback_count']
    if total != receipt['tlp_count']:
        raise ValueError('Retained TLP count disagrees with its import receipt')
    return receipt, probes, total


def retained_rows(root, probes, total, binding, cancelled):
    if total == 0:
        return [], {'source': 'verified count', 'unknown_type_rows': 0, 'omitted_rows': 0,
                    'metadata_total': 0}
    manifest = probe.read_json(root / 'triage-input.json')
    if manifest.get('schema_version') != 'pcie.triage-input/v1' or manifest['trace'] != {
        'file_name': 'display-working.pex', 'sha256': binding['display_trace_sha256'], 'tlp_count': total
    }:
        raise ValueError('Verified Fields manifest disagrees with the import')
    fields = (root / 'verified-fields/fields.json').resolve(strict=True)
    if fields.parent != root / 'verified-fields' or fields != Path(manifest['fields']['path']).resolve(strict=True):
        raise ValueError('Verified Fields path escaped this import')
    rows_path = fields
    dense = manifest.get('storage') is not None
    if dense:
        rows_path = (root / 'transactions.sqlite').resolve(strict=True)
        official_digest = manifest['storage']['sha256']
        seal = probe.read_json(root / 'disk-index.json')
        if (rows_path.parent != root or manifest['storage']['schema'] != disk.FORMAT
                or seal.get('status') != 'SEALED' or seal.get('sha256') != official_digest
                or seal.get('display_sha256') != binding['display_trace_sha256'] or seal.get('total') != total
                or seal['raw_sha256']['fields'] != probes['fields']['log_sha256']):
            raise ValueError('Retained disk index binding disagrees with the import')
    else:
        # Verify the original VSE bytes while using the persisted canonical verification.
        coverage.bound_log(root, 'fields.txt', probes['fields'])
        official_digest = manifest['fields']['sha256']
    if large.identity(rows_path, cancelled)['sha256'] != official_digest:
        raise ValueError('Retained TLP metadata changed after import')
    opened = disk.Fields(rows_path) if dense else None
    try:
        if not dense:
            large.check_file(rows_path)
        source = opened if dense else probe.read_json(rows_path)
        if len(source) != total:
            raise ValueError('Retained TLP count changed after import')
        kept, relevant, unknown = [], 0, 0
        previous = -1
        for ordinal, row in enumerate(source, 1):
            if ordinal % 512 == 0 and cancelled():
                raise InterruptedError('Cancelled while checking retained TLP metadata')
            packet = row['packet_index']
            if (row['row'] != ordinal or type(packet) is not int
                    or not previous < packet < binding['native_packet_count']):
                raise ValueError('Retained TLP Packet ordering or range is invalid')
            previous = packet
            code = int(row['tlp_type_hex'], 16)
            if kind_of(code) is not None:
                relevant += 1
                if len(kept) < MAX_RETAINED_ROWS:
                    kept.append(row)
            elif g2b.VENDOR_TLP_TYPES.get(code) not in g2b.POSTED_OR_OTHER:
                unknown += 1
    finally:
        if opened is not None:
            opened.close()
    return kept, {'source': rows_path.name, 'source_sha256': official_digest,
                  'unknown_type_rows': unknown, 'omitted_rows': relevant-len(kept),
                  'metadata_total': relevant}


def phase_boundaries(root, output, probes, receipt, binding):
    if 'phase' not in probes:
        return [], False, None
    native_version = receipt.get('capabilities', {}).get('file_version')
    phase_binding = dict(binding, native_version=native_version, segment_index=None)
    values = phase.load(root, probes['phase'], phase_binding, binding['native_packet_count'])
    qualified = phase.VERIFIED_LINK_ENUMS.get(native_version)
    verified = qualified and all(values['constants'][k] == v for k, v in qualified.items())
    seen = []
    complete = bool(verified and values['counts']['LINK_CONDITION']['count'] <= phase.CAPS['LINK_CONDITION'])
    for row in values['events']:
        if row.get('semantic') == 'LINK_DOWN' and row['semantic_status'] == 'VERSION_MAPPING_VERIFIED':
            if row['direction'] in DIRECTIONS:
                seen.append(row['packet_index'])
            else:
                complete = False
    destination = output / 'phase.txt'
    shutil.copyfile(root / 'phase.txt', destination)
    digest = nav.digest(destination)
    if digest != probes['phase']['log_sha256']:
        raise ValueError('Retained phase evidence changed during copying')
    return sorted(set(seen)), complete, dict(file=destination.name, sha256=digest)


def make_events(rows, output):
    path = output / 'retained-metadata.jsonl'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(',', ':'), ensure_ascii=False) + '\n')
    digest = nav.digest(path)
    events = {}
    for line, row in enumerate(rows, 1):
        event = metadata_event(row)
        keys = ['packet_index', 'kind']
        keys.extend(key for key in ('time_display', 'direction', 'requester_id', 'tag', 'device_id', 'status')
                    if event[key] not in (None, '', 'UNKNOWN'))
        event['evidence'].append(reference('METADATA_ONLY', path.name, digest, line, keys))
        events[event['packet_index']] = event
    return events


def add_raw(path, rows, events, total):
    large.check_file(path)
    text = path.read_text(encoding='utf-8')
    if text.splitlines().count(g1a.DONE_MARKER) != 1 or g1a.RUNTIME_ERROR_RE.search(text):
        raise ValueError('B2a did not establish a normal traversal')
    native, end = b2a.parse(text)
    wanted = [row for row in rows if int(row['tlp_type_hex'], 16) in RAW_TYPES]
    if end['tlps'] != total or len(native) != len(wanted):
        raise ValueError('B2a coverage disagrees with the retained TLP stream')
    digest = nav.digest(path)
    unsupported = weak_payload = 0
    line_numbers = (i for i, line in enumerate(text.splitlines(), 1) if line.startswith('B2A_ROW|'))
    for row, previous, line in zip(native, wanted, line_numbers):
        packet = row['packet_index']
        verified = dict(previous, row=1)
        try:
            b2a.verify([row], {'tlps': 1, 'rows': 1}, [verified], require_full_payload=True)
        except ValueError as error:
            if str(error) == 'Unsupported frame layout' or (str(error) == 'Missing frame prefix' and row['frame_prefix'] is None):
                unsupported += 1
                continue
            if str(error) != 'Full raw DWORD/payload bytes required for qualification':
                raise
            # Legacy 16-byte frame prefixes can verify headers. Never promote their DWORD.
            b2a.verify([row], {'tlps': 1, 'rows': 1}, [verified])
            weak_payload += 1
        event = events[packet]
        fields = dict(payload_bytes=row['payload_length'])
        typ = row['tlp_type']
        if typ in b2a.CFG:
            # The supported Config header carries literal Length=1 for both read and write.
            first_header = bytes.fromhex(row['frame_prefix'])
            if int.from_bytes(first_header[5:7], 'big') & 0x3FF != 1:
                raise ValueError('Config request did not have Length=1')
            fields.update(device_id=row['device_id'], register=row['register'], length_dw=1,
                          first_be=row['first_be'], last_be=row['last_be'])
        else:
            byte_count = row['byte_count']
            if byte_count == 0 and typ == 18 and event['status'] == 'SC' and row['payload_length'] > 0:
                byte_count = 4096
            fields.update(device_id=row['completer_id'], status=event['status'],
                          byte_count=byte_count, lower_address=row['lower_addr'])
        if row['payload_length'] >= 4 and len(row['frame_prefix']) == 38:
            fields['value'] = int.from_bytes(bytes.fromhex(row['payload_prefix'][:8]), 'little')
        event.update(fields)
        keys = ['packet_index', 'kind', 'requester_id', 'tag']
        if event['direction'] in DIRECTIONS:
            keys.append('direction')
        event['evidence'].append(reference('RAW_FRAME_VERIFIED', path.name, digest, line, keys + list(fields)))
    return unsupported, weak_payload


def detail_anchors(events, link_downs):
    """Select evidence windows only. The offline analyzer decides association."""
    barriers = iter(link_downs)
    barrier = next(barriers, None)
    recent = defaultdict(list)
    memory, writes, reads = set(), set(), set()
    for packet, event in events.items():
        while barrier is not None and barrier <= packet:
            recent.clear()
            barrier = next(barriers, None)
        if event['kind'] in ('CfgWr0', 'CfgWr1'):
            writes.add(packet)
        elif event['kind'] in CONFIG_KINDS:
            reads.add(packet)
        direction = event['direction']
        if event['requester_id'] is None or event['tag'] is None or direction not in DIRECTIONS:
            continue
        key = (event['requester_id'], event['tag'])
        if event['kind'] in MEMORY_KINDS.values():
            recent[key + (direction,)].append(packet)
        elif event['kind'] in COMPLETION_KINDS and event['status'] in ('UR', 'CA'):
            opposite = 'Downstream' if direction == 'Upstream' else 'Upstream'
            candidates = recent.get(key + (opposite,), ())
            if candidates:
                memory.update(candidates[-MAX_DETAIL_ANCHORS:])
                memory.add(packet)
    return memory, writes, reads


def detail_plan(events, link_downs, count):
    memory, writes, reads = detail_anchors(events, link_downs)
    planned = []
    kept = 0
    for targets, gap, after in ((memory, 12, 2), (writes, 150, 4), (reads, 12, 2)):
        for packet in sorted(targets):
            first, last = max(0, packet - 1), min(count - 1, packet + after)
            for window in planned:
                size = max(last, window['last']) - min(first, window['first']) + 1
                if size <= MAX_DETAIL_SPAN and first <= window['last'] + gap and last >= window['first'] - gap:
                    break
            else:
                if len(planned) == detail.MAX_WINDOWS or kept >= MAX_DETAIL_ANCHORS:
                    continue
                window = dict(first=first, last=last, anchors=[])
                planned.append(window)
            if kept >= MAX_DETAIL_ANCHORS:
                continue
            window['first'] = min(first, window['first'])
            window['last'] = max(last, window['last'])
            window['anchors'].append(dict(packet_index=packet, reason='config_or_ur_evidence'))
            kept += 1
    return sorted(planned, key=lambda window: window['first']), len(memory | writes | reads) - kept


MRD = re.compile(r'\bMRd\((32|64)\)\([01]{3}:[01]{5}\)')
TEXT_FIELDS = {
    'requester_id': re.compile(r'\bRequesterID\(([0-9A-Fa-f]{1,3}):([0-9A-Fa-f]{1,2}):([0-7])\)'),
    'tag': re.compile(r'\bTag\((\d+)\)'),
    'address': re.compile(r'\bAddress\((?:0x)?([0-9A-Fa-f]{1,16})\)'),
    'length_dw': re.compile(r'\bLength\((\d+)\)'),
    'first_be': re.compile(r'\b1st BE\(([01]{4})\)'),
    'last_be': re.compile(r'\bLast BE\(([01]{4})\)'),
}


def text_enrichment(row, event, type_code):
    if row['direction'] != event['direction'] or row['direction'] not in DIRECTIONS:
        return {}
    text = row['native_text']
    requester = TEXT_FIELDS['requester_id'].search(text)
    tag = TEXT_FIELDS['tag'].search(text)
    if not requester or not tag:
        return {}
    bus, device, function = (int(value, 16) for value in requester.groups())
    if bus > 0xFF or device > 0x1F or (bus << 8 | device << 3 | function) != event['requester_id']:
        return {}
    if int(tag[1]) != event['tag']:
        return {}
    result = {}
    if event['kind'] in MEMORY_KINDS.values():
        role = MRD.search(text)
        fields = {name: TEXT_FIELDS[name].search(text) for name in ('address', 'length_dw', 'first_be', 'last_be')}
        if not role or int(role[1]) != {1: 32, 4: 64}.get(type_code) or not all(fields.values()):
            return {}
        address = int(fields['address'][1], 16)
        length = int(fields['length_dw'][1]) or 1024
        if address >= (1 << int(role[1])) or address % 4 or length > 1024:
            return {}
        result.update(address=address, length_dw=length, first_be=int(fields['first_be'][1], 2),
                      last_be=int(fields['last_be'][1], 2))
    else:
        role = g2b.VENDOR_TLP_TYPES[type_code]
        if not re.search(r'\b' + re.escape(role) + r'\([01]{3}:[01]{5}\)', text):
            return {}
    stamp = row.get('timestamp_seconds')
    if stamp is not None:
        ns = Decimal(stamp) * 10**9
        if ns == ns.to_integral_value():
            result['time_ns'] = int(ns)
    return result


def add_details(data, rows, events):
    codes = {row['packet_index']: int(row['tlp_type_hex'], 16) for row in rows}
    enriched, requested = set(), set()
    for window in data['windows']:
        requested.update(anchor['packet_index'] for anchor in window['anchors'])
        for row in window['rows']:
            packet = row['packet_index']
            if packet not in events or packet in enriched:
                continue
            event = events[packet]
            values = text_enrichment(row, event, codes[packet])
            if values:
                event.update(values)
                ref = row['evidence_ref']
                event['evidence'].append(reference('NATIVE_TEXT_VERIFIED', Path(ref['path']).name,
                    ref['sha256'], ref['line'], ['packet_index', 'requester_id', 'tag', 'direction', *values]))
                enriched.add(packet)
    return len(requested - enriched)


def stage(output, name, **extra):
    probe.write(output / 'worker-progress.json', dict(stage=name, **extra))


def check_cancel(cancelled):
    if cancelled():
        raise InterruptedError('Supplemental PCIe acquisition cancelled')


def acquire_native(work, output, binding, version, raw_requested, plan, cancelled, receipt):
    import pythoncom
    import win32com.client
    from a1_com_g1a_probe import EVENTS, VseEvents

    script = Path(b2a.__file__).with_name('b2a-register-probe.pevs')
    script_identity = nav.identity(script) if raw_requested else None
    working = large.identity(work, cancelled)
    if working['sha256'] != binding['display_trace_sha256'] or not working['readonly']:
        raise ValueError('Protected display copy changed before native work')
    analyzer = trace = listener = engine = spool = None
    initialized = dispatch_started = active = False
    created = []
    receipt['existing_pids'] = probe.processes()
    if receipt['existing_pids']:
        raise RuntimeError('PETracer already has a session; supplemental analysis needs an exclusive native window')
    try:
        pythoncom.CoInitialize()
        initialized = True
        capabilities = probe.capabilities()
        if capabilities['file_version'] != version:
            raise ValueError('Installed PETracer differs from the version used for this import')
        check_cancel(cancelled)
        if probe.processes():
            raise RuntimeError('PETracer appeared before dispatch; no file was opened')
        stage(output, 'opening')
        receipt['native_cleanup'] = 'unknown'
        dispatch_started = True
        analyzer = win32com.client.Dispatch('CATC.PETracer')
        created = receipt['created_pids'] = probe.processes()
        if len(created) != 1:
            raise RuntimeError('Ambiguous PETracer ownership; no file was opened')
        stage(output, 'opening', owned_pid=created[0])
        check_cancel(cancelled)
        trace = analyzer.OpenFile(str(work))
        if int(trace.GetPacketsCountEx()) != binding['native_packet_count']:
            raise ValueError('Opened trace has a different native Packet count')
        if raw_requested:
            check_cancel(cancelled)
            stage(output, 'raw', owned_pid=created[0])
            spool = large.ReportSpool(output / 'b2a-register-fields.txt')
            EVENTS['lines'], EVENTS['finished'] = spool, None
            engine = trace.GetVScriptEngine(str(script))
            listener = win32com.client.WithEvents(engine, VseEvents)
            engine.Tag = 1
            active = True
            engine.LaunchVScript()
            deadline = time.monotonic() + VSE_LIMIT
            while EVENTS['finished'] is None and time.monotonic() < deadline:
                # A bounded spool failure is surfaced after leaving the native call safely.
                pythoncom.PumpWaitingMessages()
                time.sleep(.005)
            if EVENTS['finished'] is None:
                raise TimeoutError('Native VSE did not reach its completion callback')
            active = False
            for _ in range(20):
                pythoncom.PumpWaitingMessages()
                time.sleep(.025)
            receipt['vse_finished'] = EVENTS['finished']
            spool.finish(EVENTS['finished']['result'])
            receipt['event_disconnect'] = nav.invoke(listener, 'close')
            if not receipt['event_disconnect']['ok']:
                raise RuntimeError('Could not disconnect the VSE listener')
            listener = engine = None
        check_cancel(cancelled)
        stage(output, 'detail', owned_pid=created[0])
        details = detail.acquire(trace, output, work, binding, plan, cancelled)
        check_cancel(cancelled)
    finally:
        if spool is not None:
            spool.close()
        EVENTS['lines'], EVENTS['finished'] = [], None
        if listener is not None:
            receipt['event_disconnect'] = nav.invoke(listener, 'close')
        listener = engine = None
        if trace is not None and not active:
            receipt['close'] = nav.invoke(trace, 'Close')
        trace = analyzer = None
        if initialized:
            gc.collect()
            pythoncom.CoUninitialize()
        if dispatch_started:
            deadline = time.monotonic() + CLOSE_LIMIT
            remaining = receipt['remaining_pids'] = probe.processes()
            while len(created) == 1 and created[0] in remaining and time.monotonic() < deadline:
                time.sleep(.2)
                remaining = receipt['remaining_pids'] = probe.processes()
            closed = receipt.get('close', {'ok': not active})['ok']
            detached = receipt.get('event_disconnect', {'ok': True})['ok']
            if len(created) == 1 and created[0] not in remaining and closed and detached and not active:
                receipt['native_cleanup'] = 'confirmed'
        if large.identity(work) != working or (raw_requested and nav.identity(script) != script_identity):
            raise ValueError('Protected input changed during supplemental native work')
    return details


def collect(work, root, output, binding, cancelled, receipt):
    stage(output, 'verifying')
    if work != (root / 'display-working.pex').resolve(strict=True) or work.parent != root:
        raise ValueError('Supplemental work requires this import’s protected display-working.pex')
    working = large.identity(work, cancelled)
    if working['sha256'] != binding['display_trace_sha256'] or not working['readonly']:
        raise ValueError('Supplemental display copy failed its read-only or SHA-256 check')
    imported, probes, total = validate_import(root, working, binding)
    rows, state = retained_rows(root, probes, total, binding, cancelled)
    link_downs, boundaries_complete, phase_ref = phase_boundaries(root, output, probes, imported, binding)
    events = make_events(rows, output)
    plan, unselected = detail_plan(events, link_downs, binding['native_packet_count'])
    needs_raw = any(int(row['tlp_type_hex'], 16) in RAW_TYPES for row in rows)
    raw_requested = needs_raw and total <= MAX_RAW_TLPS and state['omitted_rows'] == 0
    details = {'windows': [], 'status': 'not_requested'}
    unsupported = weak_payload = 0
    if raw_requested or plan:
        details = acquire_native(work, output, binding, imported['capabilities']['file_version'],
                                 raw_requested, plan, cancelled, receipt)
    if receipt['native_cleanup'] != 'confirmed':
        raise CleanupUnknown('Supplemental native process cleanup could not be confirmed')
    check_cancel(cancelled)
    stage(output, 'validating')
    if raw_requested:
        unsupported, weak_payload = add_raw(output / 'b2a-register-fields.txt', rows, events, total)
    detail_missing = add_details(details, rows, events)
    unknown_keys = sum(event['requester_id'] is None or event['tag'] is None
                       or event['direction'] not in DIRECTIONS for event in events.values())
    metadata_complete = not (state['omitted_rows'] or state['unknown_type_rows'] or unknown_keys)
    return dict(schema=SCHEMA, **binding, events=list(events.values()), link_downs=link_downs,
                coverage=dict(stream_complete=metadata_complete, link_boundaries_complete=boundaries_complete,
                    full_trace_coverage='UNKNOWN', unsupported_frame_rows=unsupported,
                    omitted_rows=state['omitted_rows'], metadata_source=state,
                    unknown_key_rows=unknown_keys, weak_payload_rows=weak_payload,
                    phase_evidence=phase_ref, native_detail_status=details['status'],
                    native_detail_unselected_anchors=unselected, native_detail_missing_anchors=detail_missing,
                    raw_status='verified' if raw_requested else 'bounded_skip' if needs_raw else 'not_observed'))


def worker(request_path):
    request_path = Path(request_path).resolve(strict=True)
    output = request_path.parent
    receipt = {'status': 'error', 'native_cleanup': 'confirmed'}
    try:
        request = probe.read_json(request_path)
        binding = read_binding(request['binding'])
        work = Path(request['working']).resolve(strict=True)
        root = Path(request['analysis_root']).resolve(strict=True)
        if output.parent != root.parent or not output.name.startswith('config-ur-'):
            raise ValueError('Supplemental output escaped this case folder')
        cancelled = lambda: (output / 'cancel.json').exists()
        check_cancel(cancelled)
        observations = collect(work, root, output, binding, cancelled, receipt)
        destination = output / 'observations.json'
        large.write_json_bounded(destination, observations)
        receipt.update(status='complete', observations_sha256=nav.digest(destination))
    except InterruptedError as error:
        receipt.update(status='cancelled', error=str(error))
    except TimeoutError as error:
        receipt.update(status='timeout', error=str(error))
    except Exception as error:
        receipt.update(error=str(error))
    probe.write(output / 'acquisition-worker.json', receipt)
    return 0 if receipt['status'] == 'complete' else 1


PROGRESS = {
    'verifying': '核對唯讀工作副本與已驗證的 PCIe 交易 metadata',
    'opening': '開啟唯讀工作副本並核對 Packet 範圍',
    'raw': '擷取 Config 和 Completion 原始欄位',
    'detail': '擷取 UR／CA 附近的原生 Packet 明細',
    'validating': '交叉核對 Config、Completion 和原生 Packet 明細',
}


def run(working, analysis_root, output, binding, cancel=None, progress=lambda _: None):
    """Run under the desktop controller's existing native-exclusivity mutex."""
    working = Path(working).resolve(strict=True)
    root = Path(analysis_root).resolve(strict=True)
    output = Path(output).resolve(strict=True)
    if output.parent != root.parent or not output.name.startswith('config-ur-') or any(output.iterdir()):
        raise ValueError('Supplemental output must be a fresh Config/UR directory inside this case')
    cancelled = cancel.is_set if cancel is not None else lambda: False
    check_cancel(cancelled)
    binding = read_binding(binding)
    limits = large.policy()
    large.check_disk(output, 4 * detail.MAX_BYTES + limits['max_probe_bytes'] + 2 * limits['max_model_bytes'])
    request_path = output / 'acquisition-request.json'
    probe.write(request_path, dict(working=str(working), analysis_root=str(root), binding=binding))
    status_path = output / 'worker-progress.json'
    cancellation_path = output / 'cancel.json'
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', str(request_path)]
    with (output / 'acquisition.log').open('xb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        with supervised_worker(process, output):
            deadline = time.monotonic() + TIME_LIMIT
            announced = None
            while process.poll() is None:
                if cancelled() and not cancellation_path.exists():
                    probe.write(cancellation_path, {'requested': True, 'mode': 'between_native_calls'})
                    progress('已要求取消。等待目前原生呼叫返回並清理。')
                status = probe.read_json(status_path) if status_path.exists() else {}
                current = status.get('stage')
                if current and announced != current and not cancelled():
                    progress(PROGRESS[current])
                    announced = current
                for pid, limit_name in ((process.pid, 'worker_private_bytes'), (status.get('owned_pid'), 'native_private_bytes')):
                    resource = resources.sample(pid) if pid else None
                    if resource and resource['private_commit_bytes'] > limits[limit_name]:
                        raise large.ResourceLimit('Supplemental worker exceeded its memory budget')
                if time.monotonic() > deadline:
                    raise TimeoutError('Supplemental worker exceeded its time budget')
                large.check_disk(output)
                time.sleep(.3)
    terminal = output / 'acquisition-worker.json'
    if not terminal.exists():
        raise CleanupUnknown('Supplemental worker exited without recording native cleanup')
    receipt = probe.read_json(terminal)
    if receipt.get('native_cleanup') != 'confirmed':
        raise CleanupUnknown('Supplemental native process cleanup remains unknown: ' + receipt.get('error', ''))
    if receipt.get('status') == 'cancelled' or cancelled():
        raise InterruptedError(receipt.get('error', 'Supplemental PCIe acquisition cancelled'))
    if receipt.get('status') == 'timeout':
        raise TimeoutError(receipt['error'])
    if receipt.get('status') != 'complete' or process.returncode != 0:
        raise RuntimeError(receipt.get('error', 'Supplemental worker failed'))
    destination = output / 'observations.json'
    if nav.digest(destination) != receipt['observations_sha256']:
        raise ValueError('Supplemental observations changed after acquisition')
    observations = probe.read_json(destination)
    if observations.get('schema') != SCHEMA or any(observations.get(key) != value for key, value in binding.items()):
        raise ValueError('Supplemental observations belong to another import')
    return observations


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--worker':
        sys.exit('Use the desktop controller to start supplemental PCIe acquisition')
    sys.exit(worker(sys.argv[2]))
