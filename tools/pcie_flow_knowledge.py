"""Offline, pinned guidance. No text field can authorize a normative verdict."""
import hashlib
import json
from pathlib import Path
import pcie_next_actions as actions

ROOT=Path(__file__).resolve().parents[1]/'knowledge/pcie'
CLASSES={'OBSERVED','EXPECTED_CONTEXT','CHECK_RECOMMENDED','EVIDENCE_GAP','NOT_EVALUATED'}

def load(root=ROOT):
    root=Path(root)
    schema=json.loads((root/'rule-cards.schema.json').read_text(encoding='utf-8'))
    manifest=json.loads((root/'sources.json').read_text(encoding='utf-8'))
    sources={s['source_manifest_id']:s for s in manifest['sources']}
    if len(sources)!=len(manifest['sources']):raise ValueError('Duplicate source identity')
    cards={}
    for path in sorted((root/'cards').glob('*.json')):
        card=json.loads(path.read_text(encoding='utf-8'))
        if set(card)!=set(schema['required']):raise ValueError('Missing or unsupported knowledge fields')
        for key,spec in schema['properties'].items():
            value=card[key]
            if spec['type']=='string' and (not isinstance(value,str) or not value.strip()):raise ValueError('Invalid card field '+key)
            if spec['type']=='array' and (not isinstance(value,list) or not value or any(not isinstance(v,str) or not v.strip() for v in value)):raise ValueError('Invalid card list '+key)
            if 'enum' in spec and value not in spec['enum']:raise ValueError('Unsupported knowledge claim '+key)
        src=sources.get(card['source_manifest_id'])
        if not src or any(card[k]!=src[k] for k in ('source_url','revision_or_commit','license_status')):raise ValueError('Knowledge source mismatch')
        if card['source_kind']=='NORMATIVE' or card['allowed_claim_ceiling']!='GUIDANCE_ONLY' or card['output_class'] not in CLASSES:
            raise ValueError('This pack has no licensed normative acceptance rules')
        if card['rule_id'] in cards:raise ValueError('Duplicate rule')
        cards[card['rule_id']]=card
    if not cards:raise ValueError('Empty knowledge pack')
    digest=hashlib.sha256()
    for path in sorted(root.rglob('*.json')):digest.update(path.relative_to(root).as_posix().encode());digest.update(path.read_bytes())
    return dict(cards=cards,sources=sources,sha256=digest.hexdigest(),next_action_catalog=actions.load_catalog(root))

def reference(pack,rule_id,mode='UNKNOWN'):
    c=pack['cards'][rule_id];applicable=mode in c['applicable_gen_mode']
    next_actions=actions.for_card(pack,rule_id,mode)
    return dict(rule_id=rule_id,source_manifest_id=c['source_manifest_id'],source_url=c['source_url'],
        revision_or_commit=c['revision_or_commit'],source_kind=c['source_kind'],
        output_class=c['output_class'] if applicable else 'NOT_EVALUATED',
        applicability='GUIDANCE_ONLY_MODE_UNKNOWN' if mode=='UNKNOWN' else 'GUIDANCE_ONLY' if applicable else 'UNSUPPORTED_MODE',
        allowed_claim_ceiling='GUIDANCE_ONLY',explanation=c['display_text_zh_tw'],
        next_checks=[a['text'] for a in next_actions],next_actions=next_actions)
