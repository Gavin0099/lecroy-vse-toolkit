#!/usr/bin/env python3
"""Resolve standard register positions from observed capability-list reads."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b2b_config_access as b2b

SCHEMA='pcie.b2c-capability-map/v1'


def epoch_at(log,packet):
    a=log['anchors'];return 'before_disconnect' if packet<a['disconnect_packet'] else ('disconnect_interval' if packet<a['reconnect_packet'] else 'after_reconnect')


def read_image(log,device_id,packet,epoch):
    image={}
    reads=[r for r in log['accesses'] if r['device_id']==device_id and r['epoch']==epoch and r['read_value'] is not None]
    # A returned value becomes an observation at its Completion, not its request.
    for r in sorted(reads,key=lambda r:r['completions'][0]['packet_index']):
        effective=r['completions'][0]['packet_index']
        if effective>packet or epoch_at(log,effective)!=epoch:continue
        for i in range(4):
            if r['first_be'] & (1<<i):image[r['register_byte_offset']+i]={'value':(r['read_value']>>(8*i))&255,'request_packet':r['packet_index'],'completion_packet':effective,'access_id':r['access_id']}
    return image


def resolve(log,reference,device_id,packet):
    if log.get('schema')!=b2b.SCHEMA or reference.get('schema')!='pcie.register-reference/v1':raise ValueError('Unsupported schema')
    if type(packet) is not int or packet<0 or type(device_id) is not int or not 0<=device_id<=65535:raise ValueError('Invalid query')
    epoch=epoch_at(log,packet);image=read_image(log,device_id,packet,epoch)
    def value(offset,n):
        if not all(offset+i in image for i in range(n)):return None
        return sum(image[offset+i]['value']<<(8*i) for i in range(n))
    def evidence(offset,n):return [image[offset+i] for i in range(n) if offset+i in image]
    maps={name:{'byte_offset':off,'layout_source':reference['source'],'capability_evidence':[]} for name,off in reference['standard'].items()}
    header=value(14,1)
    if header is not None and header&127==0:
        for i,offset in enumerate(reference['normal_header_bars']):maps[f'BAR{i}']={'byte_offset':offset,'layout_source':reference['source'],'capability_evidence':evidence(14,1)}
    gaps=[]
    def walk(start,extended):
        nodes=[];seen=set();offset=start
        if offset is None:return nodes,False,'START_NOT_OBSERVED'
        while offset:
            if offset in seen:return nodes,False,f'CYCLE_AT_0x{offset:X}'
            if offset%4 or not (0x100<=offset<=0xFFC if extended else 0x40<=offset<=0xFC):return nodes,False,f'INVALID_POINTER_0x{offset:X}'
            seen.add(offset);n=4 if extended else 2;v=value(offset,n)
            if v is None:return nodes,False,f'HEADER_NOT_OBSERVED_0x{offset:X}'
            if extended and v in (0,0xFFFFFFFF):return nodes,False,f'NO_VALID_EXT_HEADER_0x{offset:X}'
            next_offset=(v>>20)&0xFFF if extended else (v>>8)&255
            nodes.append({'byte_offset':offset,'capability_id':v& (65535 if extended else 255),'next_byte_offset':next_offset,'evidence':evidence(offset,n)})
            offset=next_offset
        return nodes,True,None
    pointer=value(reference['standard']['CapabilityPointer'],1) if header is not None and header&127 in (0,1) else None
    conventional,complete,cgap=walk(pointer,False);extended,ecomplete,egap=walk(0x100,True)
    for nodes,ids,names in ((conventional,reference['capability_ids'],{'PCIe':['LinkControl','LinkStatus'],'PM':['PMCSR']}),(extended,reference['extended_capability_ids'],{'L1SS':['L1SSControl1','L1SSControl2']})):
        for family,n in ids.items():
            matches=[node for node in nodes if node['capability_id']==n]
            if len(matches)>1:gaps.append(f'DUPLICATE_{family}');continue
            if matches:
                node=matches[0]
                for name in names[family]:
                    offset=node['byte_offset']+reference['relative_offsets'][name]
                    if offset>4095:gaps.append(f'OUT_OF_RANGE_{name}');continue
                    maps[name]={'byte_offset':offset,'layout_source':reference['source'],'capability_evidence':node['evidence']}
    return {'schema':SCHEMA,'device_id':device_id,'bdf':b2b.g2b.bdf(device_id),'packet_index':packet,'epoch':epoch,'header_type':None if header is None else header&127,'registers':maps,'conventional_chain':{'nodes':conventional,'complete':complete,'gap':cgap,'pointer_evidence':evidence(52,1)},'extended_chain':{'nodes':extended,'complete':ecomplete,'gap':egap},'gaps':gaps,'not_established':['unobserved capability absence','full capability chain when gap remains','hardware state or writes applied','vendor register definitions']}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('log','reference','output-dir'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--device-id',type=lambda x:int(x,0),required=True);ap.add_argument('--packet',type=int,required=True)
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        doc=resolve(json.loads(a.log.read_text(encoding='utf-8')),json.loads(a.reference.read_text(encoding='utf-8')),a.device_id,a.packet)
        doc['input']={'log_sha256':b2a.sha(a.log),'reference_sha256':b2a.sha(a.reference)}
        a.output_dir.mkdir(parents=True);(a.output_dir/'capabilities.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps({'registers':{k:hex(v['byte_offset']) for k,v in doc['registers'].items()},'conventional_complete':doc['conventional_chain']['complete'],'extended_gap':doc['extended_chain']['gap']}))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
