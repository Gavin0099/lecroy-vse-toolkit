#!/usr/bin/env python3
"""Validate the bounded observation timeline contract, not product policy."""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = 'pcie.observation-timeline/v1'
EPOCHS = {'before_disconnect', 'disconnect_interval', 'after_reconnect'}
STATES = {'PASS', 'FAIL', 'INCONCLUSIVE', 'NOT_EVALUATED'}
BINDINGS = {'CAPTURE_DECLARED', 'DERIVED_VIA_PROBE', 'CORROBORATED_LEGACY'}
UNKNOWN_CLAIMS = {'effective_state': 'UNKNOWN', 'expected_state': 'UNKNOWN',
                  'policy_result': 'NOT_EVALUATED'}
FIELDS = {
    'document': 'schema capture_sha256 anchors ordering sources events intervals gaps milestones coverage limitations',
    'event': 'event_id packet_index time_display display_quantum_seconds layer kind direction routing_bdf device_epoch device_identity identity_continuity_proof classification state_claims details evidence',
    'interval': 'kind first_index last_index first_time last_time first_display_quantum_seconds last_display_quantum_seconds direction counts evidence',
    'gap': 'after_index before_index after_time before_time after_display_quantum_seconds before_display_quantum_seconds display_duration_seconds claim evidence',
    'milestone': 'id status basis summary evidence',
    'source': 'path sha256 capture_sha256 binding',
    'evidence': 'source_id json_pointer',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def time_parts(display):
    """Decimal display value and display quantum; neither is timer accuracy."""
    m = re.fullmatch(r'(\d+)(?:\.(\d+))? sec', display or '')
    require(m is not None, 'Unsupported display time')
    quantum = Decimal(1).scaleb(-len(m[2] or ''))
    return Decimal(display[:-4]), format(quantum, 'f')


def epoch_at(anchors, packet):
    return ('before_disconnect' if packet < anchors['disconnect_packet'] else
            'disconnect_interval' if packet < anchors['reconnect_packet'] else 'after_reconnect')


def pointer_value(payload, pointer):
    require(isinstance(pointer, str) and (pointer == '' or pointer.startswith('/')), 'Invalid JSON pointer')
    value = payload
    for token in pointer.split('/')[1:] if pointer else []:
        require(re.search(r'~(?![01])', token) is None, 'Invalid pointer escape')
        key = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            require(re.fullmatch(r'0|[1-9]\d*', key) is not None, 'Invalid array pointer')
            value = value[int(key)]
        else:
            value = value[key]
    return value


def evidence(source, pointer):
    return {'source_id': source, 'json_pointer': pointer}


def source_record(path, raw, capture_sha, binding):
    return {'path': str(path).replace('\\', '/'), 'sha256': sha(raw),
            'capture_sha256': capture_sha, 'binding': binding}


def packet_event(packet, display, layer, kind, direction, anchors, refs, details,
                 bdf=None, classification='OBSERVATION'):
    return {'event_id': f'packet:{packet}:{layer}:{kind}', 'packet_index': packet,
            'time_display': display, 'display_quantum_seconds': time_parts(display)[1],
            'layer': layer, 'kind': kind, 'direction': direction, 'routing_bdf': bdf,
            'device_epoch': epoch_at(anchors, packet), 'device_identity': 'UNKNOWN',
            'identity_continuity_proof': None, 'classification': classification,
            'state_claims': dict(UNKNOWN_CLAIMS), 'details': details, 'evidence': refs}


def new_document(capture_sha, anchors):
    return {'schema': SCHEMA, 'capture_sha256': capture_sha, 'anchors': anchors,
            'ordering': 'packet order; equal display times do not establish finer timing or causation',
            'sources': {}, 'events': [], 'intervals': [], 'gaps': [], 'milestones': [],
            'coverage': [], 'limitations': []}


def validate(doc, source_bytes):
    """Verify structure, byte identity and pointer existence.

    This is not source authenticity or fact recomputation. Adapters must verify
    upstream lineage and recompute their facts before calling this validator.
    """
    def fields(record, kind):
        require(isinstance(record, dict) and set(FIELDS[kind].split()) <= record.keys(), 'Missing ' + kind + ' fields')
    fields(doc, 'document')
    require(isinstance(doc['sources'], dict), 'Sources must be an object')
    require(all(isinstance(doc[key], list) for key in ('events', 'intervals', 'gaps', 'milestones', 'coverage', 'limitations')),
            'Timeline collections must be arrays')
    require(doc['schema'] == SCHEMA, 'Unsupported timeline schema')
    require(re.fullmatch(r'[0-9A-F]{64}', doc['capture_sha256']) is not None, 'Invalid capture identity')
    anchors = doc['anchors']
    a, b = anchors['disconnect_packet'], anchors['reconnect_packet']
    require(type(a) is int and type(b) is int and 0 <= a < b, 'Invalid anchors')
    require(doc['ordering'] == new_document(doc['capture_sha256'], anchors)['ordering'], 'Unsupported ordering claim')
    payloads = {}
    for name, src in doc['sources'].items():
        fields(src, 'source')
        require(src['capture_sha256'] == doc['capture_sha256'], 'Different capture source')
        require(src['binding'] in BINDINGS, 'Unsupported capture binding')
        require(name in source_bytes and sha(source_bytes[name]) == src['sha256'], 'Missing or changed source bytes')
        payloads[name] = json.loads(source_bytes[name])
    require(bool(payloads), 'No evidence sources')
    def refs(record):
        require(isinstance(record['evidence'], list) and bool(record['evidence']), 'Missing evidence')
        for ref in record['evidence']:
            fields(ref, 'evidence')
            require(ref['source_id'] in payloads, 'Unknown evidence source')
            try:
                pointer_value(payloads[ref['source_id']], ref['json_pointer'])
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError('Evidence pointer does not resolve') from exc
    def packet(value):
        require(type(value) is int and value >= 0, 'Invalid packet index')
    def display(record, name='time_display', precision='display_quantum_seconds'):
        require(record[precision] == time_parts(record[name])[1], 'Wrong display precision')
    ids, ordering = set(), []
    def detail_claims(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in UNKNOWN_CLAIMS:
                    require(item == UNKNOWN_CLAIMS[key], 'Details cannot promote state or policy')
                detail_claims(item)
        elif isinstance(value, list):
            for item in value:
                detail_claims(item)
    for event in doc['events']:
        fields(event, 'event')
        packet(event['packet_index']); display(event); refs(event)
        require(event['event_id'] == f"packet:{event['packet_index']}:{event['layer']}:{event['kind']}",
                'Event ID must match observation identity')
        require(event['event_id'] not in ids, 'Duplicate observation identity')
        ids.add(event['event_id']); ordering.append((event['packet_index'], event['event_id']))
        require(event['layer'] in {'TLP', 'LINK', 'DLLP', 'TRAINING', 'GUI'}, 'Unknown event layer')
        require(isinstance(event['kind'], str) and bool(event['kind']), 'Missing event kind')
        require(event['direction'] in {'Upstream', 'Downstream', 'UNKNOWN'}, 'Invalid direction')
        require(event['classification'] in {'OBSERVATION', 'WRITE_INTENT'}, 'Invalid classification')
        require(event['device_epoch'] == epoch_at(anchors, event['packet_index']), 'Event epoch mismatch')
        require(event['device_identity'] == 'UNKNOWN' and event['identity_continuity_proof'] is None,
                'Physical identity/continuity not established in v1')
        require(event['routing_bdf'] is None or re.fullmatch(r'[0-9A-F]{3}:[0-9A-F]{2}\.[0-7]', event['routing_bdf']) is not None,
                'Invalid routing BDF')
        require(event['state_claims'] == UNKNOWN_CLAIMS, 'Observation cannot establish applied/expected state or policy')
        require(isinstance(event['details'], dict), 'Invalid event details')
        detail_claims(event['details'])
    require(ordering == sorted(ordering), 'Events must use packet order with stable observation tie order')
    for interval in doc['intervals']:
        fields(interval, 'interval')
        refs(interval); packet(interval['first_index']); packet(interval['last_index'])
        require(interval['first_index'] <= interval['last_index'], 'Reversed interval')
        require(interval['direction'] == 'UNKNOWN', 'Counts cannot invent per-event direction')
        require(interval['kind'] == 'SEGMENT_COUNTS', 'Unsupported interval kind')
        require('packet_index' not in interval, 'Interval is not an individual packet')
        display(interval, 'first_time', 'first_display_quantum_seconds')
        display(interval, 'last_time', 'last_display_quantum_seconds')
        require(time_parts(interval['first_time'])[0] <= time_parts(interval['last_time'])[0], 'Reversed display interval')
        require(isinstance(interval['counts'], dict), 'Invalid interval counts')
        require(all(type(v) is int and v >= 0 for v in interval['counts'].values()), 'Invalid interval count')
    for gap in doc['gaps']:
        fields(gap, 'gap')
        refs(gap); packet(gap['after_index']); packet(gap['before_index'])
        require(gap['after_index'] < gap['before_index'] and 'packet_index' not in gap, 'Gap has no synthetic packet')
        start = time_parts(gap['after_time'])[0]; end = time_parts(gap['before_time'])[0]
        display(gap, 'after_time', 'after_display_quantum_seconds')
        display(gap, 'before_time', 'before_display_quantum_seconds')
        require(end >= start and Decimal(gap['display_duration_seconds']) == end - start, 'Invalid display gap')
        require(gap['claim'] == 'NO_OBSERVED_EVENTS_IN_SOURCE_WINDOW', 'Gap cannot prove electrical silence')
    for milestone in doc['milestones']:
        fields(milestone, 'milestone')
        refs(milestone)
        require(milestone['status'] in STATES, 'Invalid milestone status')
        require(milestone['basis'] in {'B1D_EXISTING_RULE', 'B1D_OBSERVATION_MILESTONE'}, 'Unsourced product expectation')
    require(isinstance(doc['coverage'], list) and isinstance(doc['limitations'], list), 'Missing coverage or limits')
    return {'status': 'PASS_OBSERVATION_CONTRACT', 'packet_observations': len(doc['events']),
            'distinct_observed_packets': len({r['packet_index'] for r in doc['events']}),
            'interval_summaries': len(doc['intervals']), 'gaps': len(doc['gaps'])}


def load_sources(doc, root):
    root = Path(root).resolve()
    result = {}
    require(isinstance(doc['sources'], dict), 'Sources must be an object')
    for name, source in doc['sources'].items():
        require(isinstance(source, dict) and isinstance(source.get('path'), str), 'Invalid source path')
        path = (root / source['path']).resolve()
        require(path.is_relative_to(root), 'Source outside declared root')
        result[name] = path.read_bytes()
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--timeline', type=Path, required=True)
    ap.add_argument('--source-root', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.timeline.read_text(encoding='utf-8'))
        print(json.dumps(validate(doc, load_sources(doc, args.source_root))))
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
