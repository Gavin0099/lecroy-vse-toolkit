#!/usr/bin/env python3
"""Prepare sourced register observations; require engineer scope before rules."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import b2a_register_fields as b2a
import b2e_snapshot_query as b2e
import b2c_capability_resolution as b2c

SCHEMA = 'pcie.b2g-watchlist-preparation/v2'
INTENTS = {0: 'DISABLED', 1: 'L0S', 2: 'L1', 3: 'L0S_AND_L1'}
REQUIRED_INPUTS = [
    'Target side and BDF: RC Root Port, EP, or both',
    'Applicable phase: controller connected, disconnect, SDE reconnect/training, post-L0, or entire testcase',
    'Per-register side/BDF/phase/register/bits/expected values with definition provenance',
    'Acceptance basis: write intent sufficient, or read-back / defined equivalent proof required',
]


def readback_candidates(log, write, offset):
    """Candidate reads bounded by this write and the next overlapping intent.

    Both request and completion must be in that interval. These candidates do
    not establish application of the write or select a product proof rule.
    """
    peers = [r for r in log['accesses'] if r['device_id'] == write['device_id']
             and r['epoch'] == write['epoch']]
    def selected(r):
        return {r['register_byte_offset'] + i for i in range(4) if r['first_be'] & (1 << i)}
    span = {offset, offset + 1}
    next_write = min((r['packet_index'] for r in peers
                      if r['write_value'] is not None and r['packet_index'] > write['packet_index']
                      and selected(r) & span), default=float('inf'))
    packets = []
    for r in peers:
        if (r['read_value'] is not None and span <= selected(r)
                and write['packet_index'] < r['packet_index'] < next_write
                and len(r['completions']) == 1):
            packet = r['completions'][0]['packet_index']
            if (r['packet_index'] < packet < next_write
                    and b2c.epoch_at(log,packet) == write['epoch']):
                packets.append(packet)
    return sorted(set(packets))


def build(log,ref,evaluation):
    cut=log['anchors']['disconnect_packet']-1
    observations=[]
    for device_id in sorted({r['device_id'] for r in log['accesses'] if r['epoch']=='before_disconnect'}):
        snapshot=b2e.build(log,ref,device_id,cut)
        matches=[r for r in snapshot['registers'] if 'LinkControl' in r['names']]
        if not matches:continue
        offset=matches[0]['byte_offset']
        for r in log['accesses']:
            if r['device_id']==device_id and r['epoch']=='before_disconnect' and r['register_byte_offset']==offset and r['write_value'] is not None and r['first_be'] & 1:
                bits=r['write_value'] & ref['masks']['ASPMControl']
                if bits not in INTENTS:raise ValueError('Unsupported ASPM control layout')
                read_packets=readback_candidates(log,r,offset)
                readback=bool(read_packets)
                kind='L1_ENABLE_WRITE_INTENT' if bits&2 else ('L0S_ENABLE_WRITE_INTENT' if bits&1 else 'ASPM_DISABLE_WRITE_INTENT')
                observations.append({'packet_index':r['packet_index'],'time_display':r['time_display'],'register':'PCI_EXP_LNKCTL','bdf':r['target_bdf'],'target_bdf':r['target_bdf'],'epoch':r['epoch'],'register_byte_offset':offset,'observation_kind':kind,'write_value':r['write_value'],'observed_write_intent':r['write_value']&0xFFFF if r['first_be']&3==3 else None,'first_be':r['first_be'],'aspm_control_requested_bits':bits,'aspm_control_intent':INTENTS[bits],'l0s_enable_requested':bool(bits&1),'l1_enable_requested':bool(bits&2),'completion_packets':[c['packet_index'] for c in r['completions']],'read_back_observed':readback,'read_back_evidence_packets':read_packets,'effective_state':'UNKNOWN','expected_state':'UNKNOWN','policy_result':'NOT_EVALUATED','mapping_basis':'retrospective observed capability map at pre-disconnect cut, not knowledge at write time','evidence_access_id':r['access_id']})
    return {'schema':SCHEMA,'status':'SOURCE_SCOPE_GATE','product_rule_evaluation':'NOT_EVALUATED','implemented_product_watchlist_rules':[],'product_policy':{'target_sides':None,'bdfs':None,'phases':None,'register_expectations':None,'acceptance_basis':None},'test_condition_source':{'engineer_question':8,'provenance':evaluation['product_context']['provenance'],'case_condition':evaluation['product_context']['case']['reported_symptom'],'scope_definition':None},'layout_source':ref['source'],'observations':observations,'required_inputs':list(REQUIRED_INPUTS),'not_established':['system ASPM enabled from endpoint write alone','register write applied without qualified effective-state proof','violation of unspecified product rule','new SDE identity or initialization state','hang/BSOD root cause'],'preserved_milestones':['B1d COMPLETE','MUX_CONNECTIVITY PASS','BIDIRECTIONAL_L0 PASS'],'b1d_validation_debt_blocks_v1':False}


def render(doc):
    lines=['# B2g watchlist preparation v2','','SOURCE/SCOPE GATE：產品規則待工程師指定，不是 B2g FAILED。以下只解碼 write intent；effective state、expected state 與 policy result 各自保留。','','| Packet | Time | Target | Observation | Write intent | ASPM intent | Effective state | Expected state | Policy result |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in doc['observations']:
        intent='UNKNOWN' if r['observed_write_intent'] is None else f"0x{r['observed_write_intent']:X}"
        lines.append(f"| {r['packet_index']} | {r['time_display']} | {r['bdf']} | {r['observation_kind']} | {intent} | {r['aspm_control_intent']} | {r['effective_state']} | {r['expected_state']} | {r['policy_result']} |")
    lines+=['','CfgWr／Completion acknowledgement 只支持 request 意圖與回覆；不推成 register applied、system ASPM enabled、test condition violation 或 root cause。Read-back 候選 packet 留在 JSON，不自動選擇驗收依據。']
    lines+=['','需要工程師補的規則：','']+[f'- {r}' for r in doc['required_inputs']]
    lines+=['',f"Layout source: [{doc['layout_source']}]({doc['layout_source']})",'','B1d 維持 COMPLETE，既有接通／L0 結果不重開；四項 validation debt 不阻擋 B1d。','']
    return '\n'.join(lines)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('log','reference','evaluation','output-dir'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        if a.output_dir.exists():raise ValueError('Refusing existing output')
        log=json.loads(a.log.read_text(encoding='utf-8'));ref=json.loads(a.reference.read_text(encoding='utf-8'));ev=json.loads(a.evaluation.read_text(encoding='utf-8'))
        if log['input']['b1d_evaluation_sha256']!=b2a.sha(a.evaluation):raise ValueError('Different engineer context')
        doc=build(log,ref,ev);doc['input']={'log_sha256':b2a.sha(a.log),'reference_sha256':b2a.sha(a.reference),'evaluation_sha256':b2a.sha(a.evaluation)}
        a.output_dir.mkdir(parents=True)
        (a.output_dir/'watchlist-preparation.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        (a.output_dir/'watchlist-preparation.md').write_text(render(doc),encoding='utf-8',newline='\n')
        print(json.dumps({'status':doc['status'],'product_rule_evaluation':doc['product_rule_evaluation'],'observations':len(doc['observations'])}))
    except (ValueError,OSError,KeyError,TypeError) as e:print(str(e),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
