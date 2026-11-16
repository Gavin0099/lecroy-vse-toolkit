#!/usr/bin/env python3
"""Query last observed reads and write intentions, never hardware applied state."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b2c_capability_resolution as b2c
import b2d_observed_state as b2d

SCHEMA='pcie.b2e-observed-snapshot/v1'
REGISTER_WIDTHS={'CapabilityPointer':1,'Command':2,'LinkControl':2,'LinkStatus':2,'PMCSR':2}


def query_bytes(state,offset,width):
    if type(offset) is not int or offset<0 or type(width) is not int or width not in (1,2,4) or offset+width>4096:raise ValueError('Invalid register span')
    reads=[state['read_bytes'].get(str(offset+i)) for i in range(width)]
    writes=[state['write_intent_bytes'].get(str(offset+i)) for i in range(width)]
    def value(items):return None if any(x is None for x in items) else sum(x['value']<<(8*i) for i,x in enumerate(items))
    return {'byte_offset':offset,'width_bytes':width,'read_value':value(reads),'write_intent_value':value(writes),'read_bytes':reads,'write_intent_bytes':writes,'read_has_later_write':any(w is not None and r is not None and w['request_packet']>r['completion_packet'] for r,w in zip(reads,writes)),'read_evidence_packets':sorted({r['completion_packet'] for r in reads if r is not None}),'write_evidence_packets':sorted({w['request_packet'] for w in writes if w is not None})}


def build(log,reference,device_id,packet,requested=()):
    state=b2d.build(log,device_id,packet);mapping=b2c.resolve(log,reference,device_id,packet)
    spans={}
    for name,r in mapping['registers'].items():spans.setdefault((r['byte_offset'],REGISTER_WIDTHS.get(name,4)),[]).append(name)
    for a in log['accesses']:
        if a['device_id']==device_id and a['epoch']==state['epoch'] and a['packet_index']<=packet:spans.setdefault((a['register_byte_offset'],4),[])
    for offset,width in requested:spans.setdefault((offset,width),[])
    registers=[{**query_bytes(state,offset,width),'names':names} for (offset,width),names in sorted(spans.items())]
    return {'schema':SCHEMA,'device_id':device_id,'bdf':state['bdf'],'packet_index':packet,'epoch':state['epoch'],'registers':registers,'capability_coverage':{k:mapping[k] for k in ('conventional_chain','extended_chain','gaps')},'not_established':state['not_established']}


def render(doc):
    value=lambda v:'UNKNOWN' if v is None else f'0x{v:X}'
    lines=[f"# Observed snapshot：{doc['bdf']} @ Packet {doc['packet_index']}",'',f"Epoch：{doc['epoch']}。Last read 與 last write intent 分開；不是硬體 snapshot。",'', '| Offset | Width | 名稱 | Last read | Read evidence | Last write intent | Write evidence | Read 後有 write |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['registers']:lines.append(f"| 0x{r['byte_offset']:X} | {r['width_bytes']} | {', '.join(r['names']) or 'raw offset'} | {value(r['read_value'])} | {r['read_evidence_packets']} | {value(r['write_intent_value'])} | {r['write_evidence_packets']} | {r['read_has_later_write']} |")
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('log','reference','output-dir'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--device-id',type=lambda x:int(x,0),required=True);ap.add_argument('--packet',type=int,required=True)
    ap.add_argument('--register',action='append',default=[],help='Raw byte offset:width, e.g. 0x90:2')
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        requested=[tuple(int(x,0) for x in item.split(':')) for item in a.register]
        doc=build(json.loads(a.log.read_text(encoding='utf-8')),json.loads(a.reference.read_text(encoding='utf-8')),a.device_id,a.packet,requested)
        doc['input']={'log_sha256':b2a.sha(a.log),'reference_sha256':b2a.sha(a.reference)}
        a.output_dir.mkdir(parents=True)
        (a.output_dir/'snapshot.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        (a.output_dir/'snapshot.md').write_text(render(doc),encoding='utf-8',newline='\n')
        print(json.dumps({'epoch':doc['epoch'],'registers':len(doc['registers'])}))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
