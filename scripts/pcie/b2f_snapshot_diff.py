#!/usr/bin/env python3
"""Compare observed read values and requested values with epoch boundaries."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b2e_snapshot_query as b2e

SCHEMA='pcie.b2f-observed-snapshot-diff/v1'


def compare(before,after):
    if before.get('schema')!=b2e.SCHEMA or after.get('schema')!=b2e.SCHEMA:raise ValueError('Unsupported snapshot')
    if before['packet_index']>after['packet_index']:raise ValueError('Reversed query order')
    same=before['device_id']==after['device_id'] and before['epoch']==after['epoch']
    maps=[]
    for d in (before,after):
        m={(r['byte_offset'],r['width_bytes']):r for r in d['registers']}
        if len(m)!=len(d['registers']):raise ValueError('Duplicate register span')
        maps.append(m)
    def relation(a,b):
        if not same:return 'NOT_COMPARABLE_DEVICE_EPOCH'
        if a is None or b is None:return 'EVIDENCE_GAP'
        return 'SAME_OBSERVED_VALUE' if a==b else 'OBSERVED_VALUE_CHANGED'
    rows=[]
    for key in sorted(set(maps[0])|set(maps[1])):
        a,b=maps[0].get(key),maps[1].get(key)
        rows.append({'byte_offset':key[0],'width_bytes':key[1],'before':a,'after':b,'read_relation':relation(a['read_value'] if a else None,b['read_value'] if b else None),'write_intent_relation':relation(a['write_intent_value'] if a else None,b['write_intent_value'] if b else None)})
    return {'schema':SCHEMA,'overall_verdict':'NOT_CLAIMED','comparable_device_epoch':same,'before_query':{k:before[k] for k in ('device_id','bdf','packet_index','epoch')},'after_query':{k:after[k] for k in ('device_id','bdf','packet_index','epoch')},'registers':rows,'not_established':['hardware register changes','old/new BDF same physical device','UNKNOWN means zero, absent device or failed initialization','root cause']}


def render(doc):
    val=lambda row,key:'UNKNOWN' if not row or row[key] is None else f"0x{row[key]:X}"
    lines=['# Observed snapshot diff','','跨 epoch 不能以相同 BDF 當同一裝置。Read 與 write intent 各自比較；UNKNOWN 不補零。','','| Offset | Width | Before read | After read | Read relation | Before intent | After intent | Intent relation |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['registers']:lines.append(f"| 0x{r['byte_offset']:X} | {r['width_bytes']} | {val(r['before'],'read_value')} | {val(r['after'],'read_value')} | {r['read_relation']} | {val(r['before'],'write_intent_value')} | {val(r['after'],'write_intent_value')} | {r['write_intent_relation']} |")
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('before','after','log','reference','output-dir'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        log=json.loads(a.log.read_text(encoding='utf-8'));ref=json.loads(a.reference.read_text(encoding='utf-8'))
        snapshots=[]
        for path in (a.before,a.after):
            d=json.loads(path.read_text(encoding='utf-8'))
            if d['input']!={'log_sha256':b2a.sha(a.log),'reference_sha256':b2a.sha(a.reference)}:raise ValueError('Different input identities')
            expected=b2e.build(log,ref,d['device_id'],d['packet_index'],[(r['byte_offset'],r['width_bytes']) for r in d['registers']])
            if expected!={k:v for k,v in d.items() if k!='input'}:raise ValueError('Snapshot differs from source evidence')
            snapshots.append(d)
        doc=compare(*snapshots);doc['input']={'before_sha256':b2a.sha(a.before),'after_sha256':b2a.sha(a.after),'log_sha256':b2a.sha(a.log),'reference_sha256':b2a.sha(a.reference)}
        a.output_dir.mkdir(parents=True)
        (a.output_dir/'diff.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        (a.output_dir/'diff.md').write_text(render(doc),encoding='utf-8',newline='\n')
        print(json.dumps({'registers':len(doc['registers']),'comparable_device_epoch':doc['comparable_device_epoch']}))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
