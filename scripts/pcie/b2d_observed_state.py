#!/usr/bin/env python3
"""Keep last read observations and write intentions separately, by byte and epoch."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b2b_config_access as b2b
import b2c_capability_resolution as b2c

SCHEMA='pcie.b2d-observed-config-state/v1'


def build(log,device_id,packet):
    if log.get('schema')!=b2b.SCHEMA:raise ValueError('Unsupported access log')
    if type(packet) is not int or packet<0 or type(device_id) is not int or not 0<=device_id<=65535:raise ValueError('Invalid query')
    epoch=b2c.epoch_at(log,packet)
    reads=b2c.read_image(log,device_id,packet,epoch)
    writes={}
    for r in log['accesses']:
        if r['device_id']!=device_id or r['epoch']!=epoch or r['packet_index']>packet or r['write_value'] is None:continue
        if type(r['write_value']) is not int or not 0<=r['write_value']<=0xFFFFFFFF:raise ValueError('Invalid write DWORD')
        if type(r['first_be']) is not int or not 0<=r['first_be']<=15:raise ValueError('Invalid byte enable')
        for i in range(4):
            if r['first_be'] & (1<<i):writes[r['register_byte_offset']+i]={'value':(r['write_value']>>(8*i))&255,'request_packet':r['packet_index'],'access_id':r['access_id']}
    return {'schema':SCHEMA,'device_id':device_id,'bdf':b2b.g2b.bdf(device_id),'packet_index':packet,'epoch':epoch,'read_bytes':{str(k):v for k,v in sorted(reads.items())},'write_intent_bytes':{str(k):v for k,v in sorted(writes.items())},'not_established':['hardware current value or write applied','unobserved byte value','old device state after MUX reconnect','status/W1C register effects']}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--log',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--device-id',type=lambda x:int(x,0),required=True);ap.add_argument('--packet',type=int,required=True)
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        doc=build(json.loads(a.log.read_text(encoding='utf-8')),a.device_id,a.packet);doc['input']={'log_sha256':b2a.sha(a.log)}
        a.output_dir.mkdir(parents=True);(a.output_dir/'state.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps({'epoch':doc['epoch'],'read_bytes':len(doc['read_bytes']),'write_intent_bytes':len(doc['write_intent_bytes'])}))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
