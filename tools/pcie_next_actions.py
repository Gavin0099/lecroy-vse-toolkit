"""Source-bound engineering advice; never changes protocol findings or ranking."""
import copy
import hashlib
import json
from pathlib import Path

IDENTITY = ('source_trace_sha256', 'display_trace_sha256', 'packet_namespace')
KINDS = {'ENGINEERING_RECOMMENDATION', 'EVIDENCE_REQUEST'}
SOURCE_KINDS = {'LOCAL_ENGINEERING_CONTRACT', 'VENDOR_GUIDE', 'FIELD_REFERENCE',
                'MODEL_REFERENCE', 'IMPLEMENTATION_REFERENCE'}
SAFE_TEXT = '建議補充資料：此檢查方向的來源或適用範圍尚未核對；先補足依據，再查看原生事件。'


def load_catalog(root):
    root = Path(root)
    path = root / 'next-actions.json'
    if not path.is_file():
        return dict(actions={}, card_actions={}, contract_sha256=None, contract_text='')
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 'pcie.next-action-catalog/v1':
        raise ValueError('Unsupported next action catalog')
    actions = {}
    for item in data['actions']:
        required = {'action_id', 'text_source', 'rule_ids', 'claim_kind', 'applicability',
                    'source_refs', 'required_evidence', 'limitations'}
        if set(item) != required or item['claim_kind'] not in KINDS:
            raise ValueError('Unsupported action fields or claim')
        if item['action_id'] in actions or not item['action_id']:
            raise ValueError('Duplicate or empty action identity')
        for key in ('required_evidence', 'limitations'):
            if not item[key] or any(not isinstance(v, str) or not v.strip() for v in item[key]):
                raise ValueError('Missing action evidence requirements or limitations')
        text = item['text_source']
        if not (set(text) == {'literal'} and isinstance(text['literal'], str) and text['literal'].strip()
                or set(text) == {'rule_id', 'index'} and type(text['index']) is int and text['index'] >= 0):
            raise ValueError('Invalid action text source')
        applies = item['applicability']
        if set(applies) != {'modes', 'phases', 'requires_known_direction', 'device'}:
            raise ValueError('Invalid action applicability')
        if type(applies['requires_known_direction']) is not bool or not applies['modes'] or not applies['phases']:
            raise ValueError('Missing action applicability conditions')
        if not isinstance(item['source_refs'], list) or not isinstance(item['rule_ids'], list):
            raise ValueError('Invalid action reference lists')
        for ref in item['source_refs']:
            keys = {'source_manifest_id', 'revision_or_commit', 'source_kind', 'locator', 'supports', 'limitations'}
            if set(ref) != keys or any(not isinstance(v, str) or not v.strip() for v in ref.values()):
                raise ValueError('Incomplete direct action reference')
            if ref['source_kind'] not in SOURCE_KINDS:
                raise ValueError('Unsupported source authority')
        actions[item['action_id']] = item
    mapping = data['card_actions']
    if any(not isinstance(ids, list) or not ids for ids in mapping.values()):
        raise ValueError('Invalid card action mapping')
    contract = root / 'next-action-contract.md'
    body = contract.read_bytes() if contract.is_file() else b''
    return dict(actions=actions, card_actions=mapping,
                contract_sha256=hashlib.sha256(body).hexdigest() if body else None,
                contract_text=body.decode('utf-8'))


def scope_for(model, episode=None, phase='UNBOUND'):
    scope = {key: model.get(key, 'UNKNOWN') for key in IDENTITY}
    link = (episode or {}).get('link_scope', {})
    scope.update(channel=link.get('channel', 'UNKNOWN'), direction=link.get('direction', 'UNKNOWN'),
                 epoch=link.get('epoch', 'UNKNOWN'), phase=phase,
                 device_id='UNKNOWN', physical_link_id='UNKNOWN',
                 packet_range=[episode['start_packet'], episode['end_packet']] if episode else None)
    return scope


def _sources(pack, definition):
    refs, issues = [], []
    catalog = pack['next_action_catalog']
    for ref in definition.get('source_refs', []):
        ref = copy.deepcopy(ref)
        source = pack['sources'].get(ref.get('source_manifest_id'))
        status = 'REFERENCE_MATCHED'
        if not source:
            status = 'MISSING_SOURCE'
        elif ref.get('revision_or_commit') != source.get('revision_or_commit'):
            status = 'REVISION_MISMATCH'
        elif ref.get('locator') not in source.get('action_locators', []):
            status = 'LOCATOR_NOT_REVIEWED'
        elif ref['source_manifest_id'] == 'local-action-contract':
            if source.get('content_sha256') != catalog['contract_sha256'] or not catalog['contract_sha256']:
                status = 'CONTRACT_HASH_MISMATCH'
            elif 'id="' + ref['locator'].lstrip('#') + '"' not in catalog['contract_text']:
                status = 'MISSING_CONTRACT_ANCHOR'
        elif not source.get('source_url', '').startswith('https://'):
            status = 'INVALID_REFERENCE_URL'
        ref.update(reference_status=status, source_url=source.get('source_url') if source else None,
                   license_status=source.get('license_status') if source else None)
        if status != 'REFERENCE_MATCHED':
            issues.append(ref.get('source_manifest_id', 'UNKNOWN') + ': ' + status)
        refs.append(ref)
    if not refs:
        issues.append('MISSING_ACTION_SOURCES')
    return refs, issues


def bind(pack, action_id, mode='UNKNOWN', scope=None, anchor=None, evidence_refs=None):
    """Unknown/missing/inapplicable support yields an evidence request, never a verdict."""
    catalog = pack['next_action_catalog']
    definition = catalog['actions'].get(action_id)
    supplied_scope = copy.deepcopy(scope or {})
    scope = scope_for({})
    scope.update(supplied_scope)
    evidence_refs = copy.deepcopy(evidence_refs or [])
    if definition is None:
        definition = dict(action_id=action_id, text_source={'literal': SAFE_TEXT}, rule_ids=[],
                          claim_kind='EVIDENCE_REQUEST', source_refs=[], required_evidence=['取得此建議的已審來源與適用條件。'],
                          limitations=['缺少 action 定義；不評估規範或裝置狀態。'],
                          applicability=dict(modes=[], phases=[], requires_known_direction=False, device='UNKNOWN'))
    refs, issues = _sources(pack, definition)
    text_source = definition['text_source']
    if 'literal' in text_source:
        text = text_source['literal']
    else:
        card = pack['cards'].get(text_source['rule_id'], {})
        checks = card.get('next_checks', [])
        if text_source['index'] >= len(checks):
            issues.append('MISSING_CARD_TEXT'); text = SAFE_TEXT
        else:
            text = checks[text_source['index']]
    if any(rule not in pack['cards'] for rule in definition['rule_ids']):
        issues.append('MISSING_RULE_CARD')
    applies = definition['applicability']
    reasons = []
    if mode not in applies['modes']:
        reasons.append('UNSUPPORTED_MODE')
    if 'ANY' not in applies['phases'] and scope['phase'] not in applies['phases']:
        reasons.append('PHASE_NOT_APPLICABLE')
    if applies['requires_known_direction'] and scope['direction'] not in ('Upstream', 'Downstream'):
        reasons.append('DIRECTION_UNKNOWN')
    bound = all(scope.get(k) not in (None, '', 'UNKNOWN') for k in IDENTITY)
    if not bound:
        reasons.append('SCOPE_UNBOUND')
    packet_range = scope.get('packet_range')
    valid_range = (isinstance(packet_range, (list, tuple)) and len(packet_range) == 2
                   and all(type(v) is int and v >= 0 for v in packet_range)
                   and packet_range[0] <= packet_range[1])
    if definition['claim_kind'] == 'ENGINEERING_RECOMMENDATION':
        if (any(scope.get(k) in (None, '', 'UNKNOWN', 'UNBOUND') for k in ('channel', 'epoch', 'phase'))
                or not valid_range):
            reasons.append('OBSERVATION_SCOPE_INCOMPLETE')
    if anchor and (any(anchor.get(k) != scope.get(k) for k in IDENTITY) or
                   any(anchor.get(k) != scope.get(k) for k in ('channel', 'direction', 'epoch'))):
        reasons.append('ANCHOR_SCOPE_MISMATCH')
    if anchor and valid_range and not packet_range[0] <= anchor['packet_index'] <= packet_range[1]:
        reasons.append('ANCHOR_RANGE_MISMATCH')
    if definition['claim_kind'] == 'ENGINEERING_RECOMMENDATION' and not evidence_refs:
        reasons.append('TRACE_EVIDENCE_MISSING')
    downgraded = bool(issues or reasons)
    kind = 'EVIDENCE_REQUEST' if downgraded else definition['claim_kind']
    limitations = list(definition['limitations']) + [r['limitations'] for r in refs if r.get('limitations')]
    limitations += ['來源核對僅比對本地已審記錄；runtime 未重新下載上游。',
                    '缺少的資料仍待取得；required_evidence 不是已滿足前提。']
    if issues or reasons:
        limitations.append('來源／適用缺口：' + ', '.join(issues + reasons))
    safe_anchor = None if any(reason.startswith('ANCHOR_') for reason in reasons) else copy.deepcopy(anchor)
    return dict(action_id=action_id, text=SAFE_TEXT if downgraded else text, reference_text=text, anchor=safe_anchor,
                external_evidence=' / '.join(definition['required_evidence']) if kind == 'EVIDENCE_REQUEST' else None,
                claim_kind=kind, allowed_claim_ceiling='GUIDANCE_ONLY', evaluation='NOT_EVALUATED',
                rule_ids=list(definition['rule_ids']), source_refs=refs,
                source_support='REFERENCE_MATCHED' if not issues else 'NOT_VERIFIED',
                applicability=dict(scope=scope, capture_mode=mode, conditions=copy.deepcopy(applies),
                                   status=(('TRACE_BOUND_EVIDENCE_REQUEST' if kind == 'EVIDENCE_REQUEST' else
                                            'BOUND_GUIDANCE_MODE_UNKNOWN' if mode == 'UNKNOWN' else 'BOUND_GUIDANCE')
                                           if not reasons and not issues else 'NOT_VERIFIED'), reasons=reasons),
                required_evidence=list(definition['required_evidence']), limitations=limitations,
                trace_evidence=evidence_refs, source_gaps=issues)


def for_card(pack, rule_id, mode='UNKNOWN'):
    ids = pack['next_action_catalog']['card_actions'].get(rule_id, ['missing:' + rule_id])
    return [bind(pack, action_id, mode) for action_id in ids]


def describe(action):
    """Plain provenance for offline reports; caller escapes HTML if necessary."""
    scope = action['applicability']['scope']
    lines = ['建議類型：' + action['claim_kind'] + '；規範評估：' + action['evaluation'],
             '適用範圍：' + json.dumps(scope, ensure_ascii=False, sort_keys=True),
             '來源支持：' + action['source_support']]
    for ref in action['source_refs']:
        lines.append('來源：' + str(ref['source_url']) + ref.get('locator', '') +
                     ' · ' + ref.get('revision_or_commit', 'UNKNOWN') + ' · ' + ref.get('source_kind', 'UNKNOWN') +
                     ' · ' + ref.get('supports', '') + ' · ' + ref['reference_status'])
    lines += ['知識卡核對前提（不是本次缺口清單）：' + s for s in action['required_evidence']]
    lines += ['限制：' + s for s in action['limitations']]
    return lines
