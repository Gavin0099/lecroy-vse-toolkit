"""Offline USB engineering references; never a protocol verdict engine."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'knowledge/usb'
CARD_IDS = {'usb2-enumeration', 'usb2-control', 'usb3-link-ltssm',
            'usb3-recovery', 'pd-negotiation', 'pd-vdm'}
SHA = re.compile(r'[0-9a-f]{64}\Z')


def load(root=ROOT):
    root = Path(root)
    seal = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    expected = {'sources.json', 'source-review.md', 'LICENSE-NOTICE.md'} | {c + '.json' for c in CARD_IDS}
    if set(seal['files']) != expected or seal['format'] != 'usb-knowledge-manifest/v1':
        raise ValueError('Invalid USB knowledge inventory')
    actual = {p.name for p in root.iterdir() if p.is_file() and p.suffix in ('.json', '.md')}
    if actual != expected | {'manifest.json'}:
        raise ValueError('Unexpected USB knowledge file')
    digest = hashlib.sha256()
    for name in sorted(expected):
        body = (root / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != seal['files'][name]:
            raise ValueError('USB knowledge pin mismatch: ' + name)
        digest.update(name.encode()); digest.update(body)
    sources = json.loads((root / 'sources.json').read_text(encoding='utf-8'))['sources']
    if not isinstance(sources, list) or len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Duplicate USB knowledge source')
    sources = {s['id']: s for s in sources}
    for s in sources.values():
        if (not SHA.fullmatch(s['content_sha256']) or not s['revision'] or not s['license']
                or s['pin_basis'] not in ('ORIGINAL_BYTES', 'AUTHORED_REVIEW_RECORD')
                or not s['locators'] or s['kind'] not in
                {'CATALOG_ONLY', 'FIELD_REFERENCE', 'IMPLEMENTATION_REFERENCE',
                 'TEST_REFERENCE', 'ENGINEERING_CONTRACT', 'VENDOR_GUIDANCE'}):
            raise ValueError('Invalid USB source metadata')
    cards = {}
    for name in sorted(CARD_IDS):
        c = json.loads((root / (name + '.json')).read_text(encoding='utf-8'))
        protocol = 'USB2' if name.startswith('usb2-') else 'USB3' if name.startswith('usb3-') else 'PD'
        if (c['id'] != name or c['protocol'] != protocol
                or c['claim_ceiling'] != 'GUIDANCE_ONLY'
                or not c['required_evidence'] or not c['limitations']
                or not c['source_refs'] or not c['revisions']):
            raise ValueError('Invalid USB knowledge card')
        for ref in c['source_refs']:
            s = sources.get(ref['source_id'])
            if (not s or s['kind'] == 'CATALOG_ONLY' or ref['locator'] not in s['locators']
                    or not ref['supports']):
                raise ValueError('Unsupported USB action source')
        for key in ('revisions', 'required_evidence', 'limitations'):
            if not isinstance(c[key], list) or any(not isinstance(v, str) or not v.strip() for v in c[key]):
                raise ValueError('Invalid USB card list: ' + key)
        cards[name] = c
    return dict(cards=cards, sources=sources, sha256=digest.hexdigest())


def present(value):
    return value is not None and value not in ('', 'UNKNOWN') and value != [] and value != {}


def evidence_valid(key, value):
    if not present(value):
        return False
    if key in ('address', 'endpoint', 'channel', 'sender', 'svid', 'object_position'):
        limits = {'address': (0, 127), 'endpoint': (0, 0), 'channel': (0, 2147483647),
                  'sender': (1, 2), 'svid': (1, 65535), 'object_position': (0, 7)}
        low, high = limits[key]
        return type(value) is int and low <= value <= high
    if key.endswith('_bytes'):
        return isinstance(value, str) and bool(re.fullmatch(r'(?:[0-9a-fA-F]{2})+', value))
    if key == 'capture_continuity':
        return value is True
    if key == 'ltssm_states':
        return isinstance(value, list) and bool(value) and all(v in
            ('Rx.Detect', 'Polling', 'U0', 'U1', 'U2', 'U3', 'Recovery', 'Hot Reset',
             'eSS.Disabled', 'eSS.Inactive', 'Compliance', 'Loopback') for v in value)
    if key == 'message_sequence':
        return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v.strip() for v in value)
    enums = {'sop': ('SOP', "SOP'", "SOP''"), 'power_role': ('SRC', 'SNK'),
             'mode': ('SS', 'SSP'), 'structured_version': ('1.0', '2.0', '2.1'),
             'direction': ('upstream', 'downstream', 'host_to_device', 'device_to_host')}
    if key in enums:
        return value in enums[key]
    if key == 'configuration_evidence':
        return isinstance(value, dict) and bool(value)
    return isinstance(value, str) and bool(value.strip()) and value != 'UNKNOWN'


def recommend(pack, card_id, protocol, scope, evidence=None, revision='UNKNOWN'):
    """Bind only supplied, source-scoped evidence, never guesses from labels."""
    c = pack['cards'][card_id]
    scope = copy.deepcopy(scope)
    evidence = copy.deepcopy(evidence or {})
    identity_ok = all(SHA.fullmatch(str(scope.get(k, ''))) for k in
                      ('source_trace_sha256', 'display_trace_sha256'))
    protocol_ok = protocol == c['protocol']
    target = scope.get('native_target', {})
    target_ok = (target.get('protocol') == protocol
                 and type(target.get('index')) is int and 0 <= target['index'] <= 2147483647
                 and type(target.get('level')) is int
                 and target.get('level') in ({3} if protocol == 'USB2' else {0} if protocol == 'USB3' else {0, 1, 3}))
    span = scope.get('time_range_ns')
    span_ok = (isinstance(span, list) and len(span) == 2
               and all(type(n) is int and n >= 0 for n in span) and span[0] <= span[1])
    if span_ok:
        stamp = target.get('timestamp_ns')
        span_ok = type(stamp) is int and span[0] <= stamp <= span[1]
    namespace_ok = scope.get('packet_namespace') == 'lecroy-usb-native'
    missing = [key for key in c['required_evidence'] if not evidence_valid(key, evidence.get(key))]
    # Never allow similarly named fields from a different trace/protocol to bind.
    if evidence.get('trace_sha256') != scope.get('source_trace_sha256'):
        missing.append('matching_evidence_trace_sha256')
    if evidence.get('protocol') != protocol:
        missing.append('matching_evidence_protocol')
    if evidence.get('observation_scope') != scope:
        missing.append('matching_observation_scope')
    if 'epoch' in c['required_evidence'] and (not present(scope.get('epoch')) or evidence.get('epoch') != scope.get('epoch')):
        missing.append('verified_epoch_scope')
    if 'channel' in c['required_evidence'] and evidence.get('channel') != target.get('channel'):
        missing.append('matching_native_channel')
    for key in ('direction', 'mode', 'sop', 'sender'):
        if key in c['required_evidence'] and evidence.get(key) != scope.get(key):
            missing.append('matching_scope_' + key)
    if protocol == 'USB2' and any(evidence.get(k) != scope.get(k) for k in ('address', 'endpoint')):
        missing.append('matching_address_endpoint')
    if identity_ok and scope['source_trace_sha256'] != scope['display_trace_sha256']:
        missing.append('verified_source_display_mapping')
    applicable = protocol_ok and (c['revisions'] == ['ANY_REVIEW'] or revision in c['revisions'])
    missing += ([] if identity_ok and target_ok and span_ok and namespace_ok else ['verified_native_scope'])
    bound = applicable and not missing
    refs = [dict(r, **{k: pack['sources'][r['source_id']][k]
                      for k in ('url', 'revision', 'kind', 'content_sha256', 'pin_basis', 'license')})
            for r in c['source_refs']]
    return dict(action_id=card_id + ':review', card_id=card_id, protocol=protocol,
                status='BOUND_GUIDANCE' if bound else 'EVIDENCE_REQUEST',
                evaluation='NOT_EVALUATED', source_support='LOCAL_REFERENCE_PINNED',
                claim_ceiling='GUIDANCE_ONLY', knowledge_sha256=pack['sha256'],
                text=c['next_check'] if bound else c['evidence_request'],
                required_evidence=c['required_evidence'], missing_evidence=list(dict.fromkeys(missing)),
                applicability=dict(protocol=protocol_ok, revision=revision, applicable=applicable,
                                   phase=c['phase'], scope=scope),
                source_refs=refs, limitations=c['limitations'])


def enrich(model, root=ROOT):
    """Add provenance to composed USB results without modifying discovery."""
    out = copy.deepcopy(model)
    try:
        pack = load(root)
    except (OSError, ValueError, KeyError, TypeError) as ex:
        for c in out['candidates'] + out.get('observations', []):
            c.pop('next_actions', None); c.pop('knowledge_notes', None)
        out['debug_knowledge'] = dict(state='unavailable', evaluation='NOT_EVALUATED', error=str(ex))
        out['limitations'].append('USB 工程知識無法驗證；保留原分析與定位，不提供來源綁定建議。')
        return out
    out['debug_knowledge'] = dict(state='available', knowledge_sha256=pack['sha256'],
                                 card_count=len(pack['cards']), evaluation='NOT_EVALUATED')
    for c in out['candidates'] + out.get('observations', []):
        protocol = c['protocol']; t = c['native_targets'][0]
        scope = dict(source_trace_sha256=out['trace_sha256'], display_trace_sha256=out['trace_sha256'],
                     packet_namespace='lecroy-usb-native', native_target=t,
                     time_range_ns=[c['start_ns'], c['end_ns']], epoch='UNKNOWN')
        if protocol == 'USB2':
            scope.update(address=c.get('address'), endpoint=c.get('endpoint'))
        evidence = dict(trace_sha256=out['trace_sha256'], protocol=protocol,
                        address=c.get('address'), endpoint=c.get('endpoint'), channel=t.get('channel'),
                        observation_scope=copy.deepcopy(scope))
        # Existing candidates do not certify reset epochs, wire direction,
        # full descriptor/PDO/RDO bytes or actual LTSSM states. Preserve that gap.
        is_descriptor = any(r.get('index') == t['index'] and r.get('request') == 6
                            and r.get('request_type') == 0 for r in c.get('context', []))
        ids = (['usb2-control'] + (['usb2-enumeration'] if is_descriptor else []) if protocol == 'USB2' else
               ['usb3-link-ltssm', 'usb3-recovery'] if protocol == 'USB3' else
               ['pd-vdm'] if any('vendor' in r.get('native', {}) and r['native'].get('vendor')
                                 for r in c.get('context', [])) else ['pd-negotiation'])
        c['next_actions'] = [recommend(pack, name, protocol, scope, evidence) for name in ids]
        detail = ['工程知識：僅供檢查，不是 Spec 違規判定。']
        for a in c['next_actions']:
            detail.append(pack['cards'][a['card_id']]['title'] + '：' + a['text'])
            if a['missing_evidence']:
                detail.append('仍需證據：' + '、'.join(a['missing_evidence']))
            detail += ['來源：' + r['url'] + ' · ' + r['locator'] for r in a['source_refs']]
        c['knowledge_notes'] = detail
    return out
