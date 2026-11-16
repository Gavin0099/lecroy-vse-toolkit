"""Evidence-led review order over r6 facts; no root-cause or timeout inference."""
import copy
from bisect import bisect_right
from collections import Counter
import pcie_flow_episodes as episodes
import pcie_flow_knowledge as knowledge
import pcie_stage_summary as stages
import pcie_next_actions as actions
import pcie_engineer_view as engineer

FORMAT='pcie.flow-triage/v1'

def completion_checks(transactions,summary,pack,mode):
    ref=knowledge.reference(pack,'CPL-01',mode)
    rows=(transactions or {}).get('rows',[])
    if any(any(r.get(k)!=summary[k] for k in episodes.IDENTITY) for r in rows):
        raise ValueError('Transaction evidence belongs to another trace or packet namespace')
    packet=[r for r in rows if r['namespace']=='packet']
    cuts=sorted({r['packet_index'] for r in summary['events'] if r['kind']=='LINK' or r['kind']=='LTSSM' and (r.get('valid')!=1 or r.get('state_name') in ('DETECT','HOT_RESET','DISABLED'))})
    requests=[r for r in packet if r['type_name'].startswith('CFG')]
    completions=[r for r in packet if r['type_name'] in ('CPL','CPLD')]
    observations=[]
    for c in completions:
        observations.append(dict(packet_index=c['index'],status=c['completion_label'],output_class='OBSERVED',
            direction=c['direction'],evidence_refs=[c['evidence_ref']],**{k:ref[k] for k in ('rule_id','source_manifest_id')}))
    counts=Counter(c['status'] for c in observations)
    status_summary='可見 Completion：'+('、'.join(k+' '+str(v)+' 筆' for k,v in sorted(counts.items())) if counts else '未取得')+'。狀態保留供覆核；未證明完整交易配對或逾時。'
    related=[]
    for r in requests:
        found=[]
        if mode!='FLIT' and r['direction']!='UNKNOWN' and r['requester_id'] is not None and r['tag'] is not None:
            found=[c for c in completions if c['index']>r['index'] and c['direction'] not in ('UNKNOWN',r['direction']) and
                   (c['requester_id'],c['tag'])==(r['requester_id'],r['tag']) and bisect_right(cuts,c['index'])==bisect_right(cuts,r['index'])]
        related.append(dict(request_packet=r['index'],requester_id=r['requester_id'],tag=r['tag'],target_id=r['target_id'],register=r['register'],
            possible_completion_packets=[c['index'] for c in found],visible_statuses=[c['completion_label'] for c in found],
            relation='SAME_KEY_OPPOSITE_DIRECTION_ONLY' if found else 'NOT_ESTABLISHED',
            transaction_complete='NOT_ESTABLISHED',retry='NOT_ESTABLISHED',replay='NOT_ESTABLISHED',
            explanation='可見同 Key 逆向 Completion；缺實體 Link／完整 Split 子封包對應，不能確認是同一交易。' if found else '本次沒有建立 Completion 配對；不表示沒有回覆或已逾時。',
            output_class='CHECK_RECOMMENDED' if found else 'EVIDENCE_GAP',rule_id=ref['rule_id'],source_manifest_id=ref['source_manifest_id'],
            evidence_refs=[r['evidence_ref']]+[c['evidence_ref'] for c in found]))
    return dict(knowledge=ref,completion_observations=observations,request_checks=related,status_summary=status_summary,
        full_split_mapping='NOT_ESTABLISHED',timeout_evaluation='NOT_EVALUATED',
        mode_status='UNSUPPORTED_MODE' if mode=='FLIT' else 'OBSERVATIONS_ONLY',
        limitations=['同 Key 不證明相同 target、同裝置或 Tag 未重用。','原生 Split 起點／狀態不等於完整子 Packet 映射。'])

def build(model,transactions=None,context=None,pack=None):
    pack=pack or knowledge.load();summary=model['stage_summary'];mode=model['coverage'].get('capture_mode','UNKNOWN')
    context=episodes.validate_context(context,model)
    values=episodes.overlay(episodes.build(summary),context)
    truncated=any(c.get('truncated') for c in model['coverage'].get('event_families',[]) if c['family'] in ('LTSSM_CHANGE','LINK_CONDITION'))
    latest={}
    for e in values:
        key=(e['link_scope']['channel'],e['link_scope']['direction'])
        if key not in latest or e['end_packet']>=latest[key]['end_packet']:latest[key]=e
    for e in values:
        a=e['focus_anchor'];current=latest[(e['link_scope']['channel'],e['link_scope']['direction'])] is e
        l0=e['current_l0'] if not truncated and mode!='FLIT' else None
        has_link=any(r['kind'] in ('LINK','LTSSM') for r in e['events'])
        if not current:
            title='較早的方向觀察區間';why='後續已有同方向的新區間；此處保留為流程背景。'
            action_id='review-later-epoch';phase='HISTORY';priority=4;cls='OBSERVED'
        elif l0:
            title='已見單方向 L0；初始化證據待核對';why='最後保留的方向狀態為有效 L0；裝置辨識與初始化仍無完成證據。'
            action_id='post-l0-config';phase='L0_OBSERVED';priority=2;cls='CHECK_RECOMMENDED';a=l0
        elif has_link:
            title='重新連線狀態待核對';why='已有 Link／Training 觀察，但沒有足夠證據沿用為目前有效 L0。'
            action_id='review-training';phase='LINK_REVIEW';priority=2;cls='CHECK_RECOMMENDED'
        else:
            title='配置交易可見；連線階段資料不足';why='可見配置請求，缺可對應的 Link／LTSSM 狀態。'
            action_id='config-scope';phase='CONFIG_ONLY';priority=3;cls='EVIDENCE_GAP'
        if mode=='FLIT':title='此擷取模式的流程分析尚未支援';why='Flit 不能套用本版非 Flit 交易關聯。';priority=3;cls='EVIDENCE_GAP'
        elif current and e['link_scope']['direction']=='UNKNOWN':
            title='事件方向未確認；無法串接連線階段';why='原生事件沒有可核實的方向，不能與其他 Channel 拼成同一 Link。';priority=3;cls='EVIDENCE_GAP'
        if any(o['output_class']=='CHECK_RECOMMENDED' for o in e['observations']):
            why+=' 工程師提供的區間不預期斷線，需獨立覆核；其他區間不受此情境影響。'
        refs=[knowledge.reference(pack,r,mode) for r in ('LTSSM-01','HOTPLUG-01','ENUM-01','CPL-01')]
        action_scope=actions.scope_for(model,e,phase)
        e.update(focus_anchor=a,title=title,output_class=cls,
            what_observed=[stages.location(m['anchor'])+'：'+m['explanation'] for m in e['milestones'][-3:]] or [stages.location(a)+'：沒有有效階段里程碑。'],
            why_inspect=why,remaining_unknowns=['實體 Link 配對與裝置身分 UNKNOWN。','全檔／顯示過濾／擷取尾端覆蓋 UNKNOWN；未觀察不等於失敗。',
                'Link／LTSSM 已達保留上限，最後保留狀態不能代表擷取尾端。' if truncated else '未證明初始化完成；沒有完整 Split 子封包配對。'],
            next_unverified_step='配置與初始化證據' if l0 else '有效連線與後續配置證據',
            next_actions=[actions.bind(pack,action_id,mode,action_scope,a,e['evidence_refs']),
                          actions.bind(pack,'collect-context',mode,action_scope)],
            priority=dict(mode='EVIDENCE_BASED' if current else 'CAPTURE_ORDER',tier=priority,reasons=[why],tie_break='latest retained anchor first; not risk probability'),
            applicable_cards=refs,spec_checks=[dict(rule_id=r['rule_id'],source_manifest_id=r['source_manifest_id'],output_class='NOT_EVALUATED',evidence_refs=e['evidence_refs'],reason='無已授權且適用版本的規範接受條件；僅執行工程核對。') for r in refs],
            packet_findings=[c['id'] for c in model['candidates'] if e['start_packet']<=c['locator']['packet_index']<=e['end_packet'] and c['locator']['direction']==e['link_scope']['direction']])
    ordered=sorted(values,key=lambda e:(e['priority']['tier'],-e['focus_anchor']['packet_index'],e['scenario_id']))
    displayed=[e['scenario_id'] for e in ordered if e['priority']['tier']<4][:3]
    primary=next((e for e in ordered if e['scenario_id'] in displayed),None)
    checks=completion_checks(transactions,summary,pack,mode)
    # Packet records are retained, never reclassified by scenario text.
    packet_refs=[]
    for c in model['candidates']:
        index=c['locator']['packet_index'];focus=primary['focus_anchor']['packet_index'] if primary else None
        packet_refs.append(dict(id=c['id'],packet_index=index,output_class='OBSERVED',
            relative_order='BEFORE_PRIMARY_ANCHOR' if focus is not None and index<focus else 'AT_PRIMARY_ANCHOR' if index==focus else 'AFTER_PRIMARY_ANCHOR' if focus is not None else 'UNKNOWN',
            phase_membership='NOT_ESTABLISHED',explanation='Packet 次序僅供核對；跨方向／epoch 不推論因果。早於階段錨點的交易不能作為該錨點之後的初始化失敗證據。',
            evidence_refs=c['evidence_refs']))
    context_text='未提供工程情境；不推定刻意 Hot Plug。' if not context else '工程師情境：'+context['description']+'（來源：'+context['source']+'；'+('範圍已指定，僅相符轉場套用' if context['scope'] else '尚未綁定轉場範圍，僅作背景')+'）'
    primary_action=primary['next_actions'][0] if primary else actions.bind(pack,'collect-capture',mode,actions.scope_for(model,phase='EMPTY'))
    presentation=dict(headline=primary['title'] if primary else '流程階段資料不足',context=context_text,
        observed='\n'.join(primary['what_observed']) if primary else '沒有足夠的可追溯階段；保留原 Packet 觀察。',
        why_inspect=primary['why_inspect'] if primary else '缺少 Link／LTSSM 或配置階段證據。',
        next_check=primary_action['text'],next_action=primary_action,
        claim_boundary='調查順序不是故障機率；單方向 L0 不代表雙向 Link 或初始化成功。',
        coverage='Coverage UNKNOWN；本次訂閱與保留範圍不代表全檔。',
        packet_summary='次要交易觀察 '+str(len(packet_refs))+' 筆；原始擷取順序與定位保持不變。',
        completion_summary=checks['status_summary'])
    return dict(schema=FORMAT,run_id=model['analysis_id'],**{k:model[k] for k in episodes.IDENTITY},
        scope=dict(filter_status='UNKNOWN',coverage='PARTIAL' if truncated else 'UNKNOWN',capture_end='UNKNOWN',mode=mode),
        knowledge_pack_sha256=pack['sha256'],expected_context=context,scenarios=values,
        priority_order=[e['scenario_id'] for e in ordered],displayed_scenarios=displayed,
        primary_scenario=primary['scenario_id'] if primary else None,packet_findings=packet_refs,
        transaction_checks=checks,presentation=presentation,root_cause='NOT_EVALUATED',device_initialization='NOT_ESTABLISHED',
        knowledge_only=[knowledge.reference(pack,r,mode) for r in ('REPLAY-01','ASPM-01')])

def cards(model,flow):
    by_id={e['scenario_id']:e for e in flow['scenarios']};result=[]
    for id in flow['priority_order']:
        e=by_id[id];a=e['focus_anchor'];t=a.get('time_object')
        ns=t[0]*1000000000+t[1] if t and len(t)==3 and all(type(v) is int for v in t) and t[2]==0 else None
        locator=dict(a,display_level=0,timestamp=dict(value=ns,unit='ns') if ns is not None else None)
        context=[dict(index=m['anchor']['packet_index'],time_display=stages.location(m['anchor']),timestamp_ns=None,
            channel=m['anchor']['direction'],message=m['kind'],result='階段觀察，非故障',detail=m['explanation'],evidence_ref=m['anchor']['evidence_ref']) for m in e['milestones']]
        interpretations=[]
        for o in e['observations']:
            if o['output_class']=='OBSERVED':continue
            label='預期情境' if o['output_class']=='EXPECTED_CONTEXT' else '工程情境待核對'
            interpretations.append(label+' · Packet '+str(o['anchor']['packet_index'])+'：'+o['interpretation'])
            for row in context:
                if row['index']==o['anchor']['packet_index']:
                    row['result']=label;row['detail']+=' '+o['interpretation']
        context_by_index={r['index']:r for r in context}
        for w in model.get('native_details',{}).get('windows',[]):
            if not any(x['packet_index']==a['packet_index'] for x in w['anchors']):continue
            for r in w['rows']:
                existing=context_by_index.get(r['packet_index'])
                if existing is not None:
                    existing.update(native_text=r['native_text'],native_evidence_ref=r['evidence_ref'])
                else:
                    context_by_index[r['packet_index']]=dict(index=r['packet_index'],time_display=(r['timestamp_seconds']+' s') if r['timestamp_seconds'] else 'UNKNOWN',
                        timestamp_ns=None,channel=r['direction'],message='階段附近原生明細',result='觀察，非故障判定',detail=r['native_text'],evidence_ref=r['evidence_ref'])
        context=[context_by_index[i] for i in sorted(context_by_index)]
        result.append(dict(rank=len(result)+1,protocol_rank=len(result)+1,protocol='PCIe',id=model['analysis_id']+':flow:'+id,
            scenario_id=id,title=e['title'],output_class=e['output_class'],locator=locator,
            native_targets=[dict(protocol='PCIe',level=0,index=a['packet_index'],timestamp_ns=ns,channel=a['channel'])],
            start_ns=ns,end_ns=ns,time_display=stages.location(a),time_precision=a['time_precision'],
            facts=e['what_observed']+interpretations,reasons=[e['why_inspect']],next_step=e['next_actions'][0]['text'],
            next_actions=copy.deepcopy(e['next_actions']),
            evidence_gaps=e['remaining_unknowns']+[line for action in e['next_actions'] for line in actions.describe(action)],
            context=context,evidence_refs=e['evidence_refs']))
    for card in result:
        engineer.enrich_card(model,flow,by_id[card['scenario_id']],card)
    return result

def attach(model,transactions=None,context=None):
    model['flow_analysis']=build(model,transactions,context)
    model['flow_items']=cards(model,model['flow_analysis'])
    model['engineer_view']=engineer.build(model,model['flow_analysis'])
    return model
