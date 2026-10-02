#!/usr/bin/env python3
"""Build observed configuration accesses from the qualified B2a probe."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b1d_mux_rules as b1d
import g2b_associate as g2b

SCHEMA = "pcie.b2b-config-access/v1"


def associate_config(metadata, fields):
    """Use all request types to reserve keys; retire only qualified config replies.

    Memory split completion semantics are not implemented. Late replies to a retired
    config key are unmatched, never appended as another config value.
    """
    pending, requests, ambiguous, unmatched = {}, [], set(), []
    indices=[r['packet_index'] for r in metadata]
    if any(b<=a for a,b in zip(indices,indices[1:])):raise ValueError('Non-increasing metadata')
    for row in metadata:
        role=g2b.classify(row);key=(row['requester_id'],row['tag'])
        if role['role']==g2b.NON_POSTED_REQUEST:
            previous=pending.get(key)
            if previous:
                previous['outcome']=g2b.REISSUED
                ambiguous.add(previous['packet_index']);ambiguous.add(row['packet_index'])
            q={**row,'vendor_type_name':role['vendor_type_name'],'outcome':g2b.NONE_OBSERVED,'completions':[]}
            pending[key]=q;requests.append(q)
        elif role['role']==g2b.COMPLETION_CANDIDATE:
            q=pending.get(key);c=fields.get(row['packet_index'])
            if c is None:
                c={**row,'tlp_type':int(row['tlp_type_hex'],16),'register_data':None,
                   'payload_length':None,'byte_count':None,'lower_addr':None,
                   'field_status':'NOT_CAPTURED_BY_B2A'}
                if q:
                    q['completions'].append(c)
                    if q['outcome']!=g2b.REISSUED:q['outcome']=g2b.COMPLETIONS_OBSERVED
                else:unmatched.append(c)
                continue
            if not q:unmatched.append(c);continue
            q['completions'].append(c)
            if q['outcome']!=g2b.REISSUED:q['outcome']=g2b.COMPLETIONS_OBSERVED
            if int(q['tlp_type_hex'],16) in b2a.CFG:
                r=fields[q['packet_index']]
                shape=(c['tlp_type']==18 and c['payload_length']==4 and c['byte_count']==4 and c['lower_addr']==0 and c['register_data'] is not None) if r['tlp_type'] in (9,11) else (c['tlp_type']==17 and c['payload_length']==0)
                if c['channel']!=r['channel'] and c['completer_id']==r['device_id'] and (c['compl_status']!=0 or shape):
                    del pending[key]
    return requests,ambiguous,unmatched


def build(probe, metadata, disconnect, reconnect):
    if probe.get('schema') != b2a.SCHEMA or probe.get('status') != 'PASS_REGISTER_FIELD_PROBE': raise ValueError('Unqualified register probe')
    if type(disconnect) is not int or type(reconnect) is not int or not 0 <= disconnect < reconnect: raise ValueError('Invalid switch anchors')
    raw=probe['rows']; b2a.verify(raw,dict(tlps=probe['tlps'],rows=len(raw)),metadata)
    fields={r['packet_index']:r for r in raw}
    requests,ambiguous,unmatched=associate_config(metadata,fields)
    accesses=[]
    for q in requests:
        if int(q['tlp_type_hex'],16) not in b2a.CFG:continue
        r=fields[q['packet_index']]
        completions=q['completions']
        data=None;value_status='UNKNOWN';is_read=r['tlp_type'] in (9,11)
        if not is_read:value_status='WRITE_REQUEST_OBSERVED'
        elif q['packet_index'] in ambiguous:value_status='AMBIGUOUS_KEY_REUSE'
        elif len(completions)==1:
            c=completions[0]
            if c['compl_status']==0 and c['channel']!=r['channel'] and c['completer_id']==r['device_id'] and c['tlp_type']==18 and c['payload_length']==4 and c['byte_count']==4 and c['lower_addr']==0 and r['first_be']==15 and r['last_be']==0 and c['register_data'] is not None:
                data=c['register_data'];value_status='READ_RETURN_OBSERVED'
        epoch='before_disconnect' if r['packet_index']<disconnect else ('disconnect_interval' if r['packet_index']<reconnect else 'after_reconnect')
        accesses.append({'access_id':f"B2B-{len(accesses)+1:03}",'packet_index':r['packet_index'],'time_display':r['time_display'],'channel':r['channel'],'type':q['vendor_type_name'],'requester_bdf':g2b.bdf(r['requester_id']),'target_bdf':g2b.bdf(r['device_id']),'device_id':r['device_id'],'requester_id':r['requester_id'],'tag':r['tag'],'register_byte_offset':r['register'],'first_be':r['first_be'],'last_be':r['last_be'],'write_value':None if is_read else r['register_data'],'read_value':data,'value_status':value_status,'association_outcome':q['outcome'],'completions':completions,'epoch':epoch,'evidence':{'probe_row':f"/rows/{raw.index(r)}",'g2a_row':f"/rows/{q['row']-1}",'packet_index':r['packet_index']}})
    return {'schema':SCHEMA,'overall_verdict':'NOT_CLAIMED','trace':probe['input']['trace'],'anchors':{'disconnect_packet':disconnect,'reconnect_packet':reconnect,'basis':'B1d context; source hashes in input'},'accesses':accesses,'unmatched_completion_candidates':unmatched,'association_strategy':'all non-posted requests reserve keys; qualified config completion retires key; memory split completeness not established','summary':{'config_requests':len(accesses),'reads':sum(x['type'] in ('CfgRd0','CfgRd1') for x in accesses),'writes':sum(x['write_value'] is not None for x in accesses),'observed_read_returns':sum(x['read_value'] is not None for x in accesses),'after_reconnect_requests':sum(x['epoch']=='after_reconnect' for x in accesses)},'not_established':['hardware snapshot or writes taking effect','protocol timeout or complete transaction correctness','post-reconnect SDE initialization beyond capture end','vendor register decode','same BDF implies same device across MUX switch']}


def render(doc):
    val=lambda v:'UNKNOWN' if v is None else f'0x{v:X}'
    lines=['# PCIe-B2b：Config access log','','此表列出 RC request 與 trace 中的回覆；寫入意圖不等同硬體生效。切換前 state 不沿用到新裝置。','','| Packet | 時間 | Epoch | Type | Target | Offset (bytes) | BE | Write | Read return | Completion |','| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['accesses']:
        cp=', '.join(f"{c['packet_index']} status={c['compl_status']}" for c in r['completions']) or 'NONE_OBSERVED'
        lines.append(f"| {r['packet_index']} | {r['time_display']} | {r['epoch']} | {r['type']} | {r['target_bdf']} | {val(r['register_byte_offset'])} | {val(r['first_be'])}/{val(r['last_be'])} | {val(r['write_value'])} | {val(r['read_value'])} | {cp} |")
    lines+=['','## 限制','']+[f'- {x}' for x in doc['not_established']]
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('probe','metadata','evaluation','training','output-dir'):ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        probe=json.loads(a.probe.read_text(encoding='utf-8'));meta=json.loads(a.metadata.read_text(encoding='utf-8'));evaluation=json.loads(a.evaluation.read_text(encoding='utf-8'))
        if b2a.sha(a.metadata)!=probe['input']['metadata_sha256']:raise ValueError('Metadata hash differs')
        context=evaluation['product_context'];training=json.loads(a.training.read_text(encoding='utf-8'))
        if b2a.sha(a.training)!=evaluation['input']['training_sha256'] or b1d.evaluate(training,context)!={k:v for k,v in evaluation.items() if k!='input'}:raise ValueError('Inconsistent B1d evidence')
        by_packet={r['packet_index']:r for r in meta}
        for r in b1d.records(training,'inner_records'):
            if r['kind']=='tlp':
                m=by_packet.get(r['packet_index'])
                if not m or (m['channel'],m['time_display'],int(m['tlp_type_hex'],16))!=(r['channel'],r['time_display'],r['tlp_type']):raise ValueError('Link/config overlap differs')
        if Path(probe['input']['trace']['path']).name!=context['case']['trace_basename']:raise ValueError('Different trace basename')
        anchors=context['operation']
        doc=build(probe,meta,anchors['disconnect_packet'],anchors['reconnect_packet'])
        doc['input']={'probe_sha256':b2a.sha(a.probe),'metadata_sha256':b2a.sha(a.metadata),'b1d_evaluation_sha256':b2a.sha(a.evaluation),'training_sha256':b2a.sha(a.training),'trace_binding':'same probe/G2a rows, matching B1c window TLPs, basename; B1c did not carry a trace hash'}
        a.output_dir.mkdir(parents=True)
        (a.output_dir/'accesses.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        (a.output_dir/'accesses.md').write_text(render(doc),encoding='utf-8',newline='\n')
        print(json.dumps(doc['summary']))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
