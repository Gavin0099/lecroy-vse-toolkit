"""Plain engineering projection of existing evidence, never a new verdict/rank."""
import copy

IDENTITY=('source_trace_sha256','display_trace_sha256','packet_namespace')


def location(anchor):
    text='Packet '+str(anchor['packet_index'])+' · '+str(anchor['direction'])
    t=anchor.get('time_object')
    if t and len(t)==3 and all(type(v) is int for v in t):
        text+=' · '+str(t[0])+'.'+str(t[1]).zfill(9)+(str(t[2]).zfill(3) if t[2] else '')+' 秒'
    else:text+=' · '+str(anchor.get('time_display') or '時間未提供')+'（原始精度）'
    return text


def build(model, flow, scenario=None):
    if scenario is None:
        scenario=next((e for e in flow['scenarios'] if e['scenario_id']==flow['primary_scenario']),None)
    if scenario is None:
        return dict(headline='連線與初始化資料不足，尚無法確認流程進度',
                    observed='目前未建立可追溯的連線階段。',
                    uncertain='不能由缺少資料判定裝置初始化失敗。',
                    next_check='請補 Link／連線狀態與配置請求、回覆的擷取資料。',
                    meaning='這是分析範圍的限制；沒有候選不代表測試通過。',
                    resolved_evidence=[],missing_evidence=['連線狀態與同一擷取範圍的配置交易'],
                    primary_anchor=None,followup_anchor=None,sequence=[],
                    action=dict(kind='EVIDENCE_REQUEST',label='查看需補資料'),
                    completion_note='全保留範圍的回覆數量不能代表本階段之後的裝置回覆。')
    e=scenario;a=e['focus_anchor'];primary=copy.deepcopy(a)
    action=e['next_actions'][0]
    l0=(action['action_id']=='post-l0-config' and e.get('current_l0') is not None
        and a['packet_index']==e['current_l0']['packet_index'])
    history=action['action_id']=='review-later-epoch'
    missing=['實體連線及目標裝置的對應','作業系統辨識／初始化結果','擷取範圍是否連續並包含結尾']
    resolved=[];followup=None
    if l0:
        headline='已觀察到單方向 L0，裝置初始化仍待確認'
        observed=a['direction']+' 方向已進入 L0（可傳輸的連線狀態）。'+location(a)+'。'
        uncertain='目前證據不足以確認目標裝置已被系統辨識或完成初始化。'
        resolved=[dict(id='directional_l0',text='有效單方向 L0 已觀察到',anchor=copy.deepcopy(a))]
        configs=[m['anchor'] for m in e['milestones'] if m['kind']=='CONFIG_REQUEST_OBSERVED'
                 and m['anchor']['packet_index']>a['packet_index']
                 and all(m['anchor'].get(k)==a.get(k) for k in (*IDENTITY,'channel','direction','epoch'))
                 and m['anchor'].get('evidence_ref')]
        if configs:
            followup=copy.deepcopy(min(configs,key=lambda c:c['packet_index']))
            next_check='查看後續配置請求 Packet '+str(followup['packet_index'])+'，核對它的回覆（Completion）與目標裝置身分。'
            missing.insert(0,'這筆配置請求的完整回覆關聯及目標裝置身分')
            resolved.append(dict(id='later_config_request',text='同方向觀察區間有較後的配置請求',anchor=followup))
        else:
            next_check='先定位此連線里程碑，再向後核對配置請求及回覆；目前保留資料尚未建立同區間的後續關聯。'
            missing.insert(0,'此里程碑之後可追溯的配置請求與回覆（Config／Completion）')
        if action['source_gaps'] or action['applicability']['reasons']:
            followup=None
            next_check='已保留連線里程碑；請先補足後續建議的來源與適用範圍，再決定進一步檢查。'
            missing.insert(0,'可支持後續建議的來源與適用範圍')
    elif history:
        headline='較早的流程觀察，供前後事件比對'
        observed='這段已有後續觀察區間；位置：'+location(a)+'。'
        uncertain='此處的狀態不能代表後續連線或初始化結果。'
        next_check='查看事件順序，再切回較後的流程；不要將不同區間的交易直接連成故障原因。'
    else:
        headline='連線恢復仍待確認，先核對後續狀態'
        observed='已保留連線或配置相關事件。位置：'+location(a)+'。'
        uncertain='目前不能確認這個方向已恢復連線，也不能判定初始化失敗。'
        next_check='先定位這個位置，查看後續是否恢復 L0；若擷取在此結束，請補後段資料。'
        missing.insert(0,'本區間後續有效連線狀態與配置交易')
        if flow['scope']['mode']=='FLIT':
            headline='此擷取模式尚未支援流程判讀';observed='已保留原始事件及交易觀察。'
            uncertain='本版不能用這種模式確認連線與初始化流程。'
            next_check='請保留原始資料，補充可支援的非 Flit 解碼或原生分析器核對結果。'
        elif e['link_scope']['direction']=='UNKNOWN':
            headline='事件方向待確認，尚不能串接連線流程'
    sequence=[]
    labels={'DIRECTION_L0_OBSERVED':'L0（可傳輸狀態）','CONFIG_REQUEST_OBSERVED':'配置請求',
            'LINK_DOWN_OBSERVED':'連線中斷','LINK_UP_OBSERVED':'連線接通'}
    for m in e['milestones'][-8:]:
        label=labels.get(m['kind'])
        if label is None:
            row=next((r for r in e['events'] if r['packet_index']==m['anchor']['packet_index'] and r['kind']=='LTSSM'),{})
            label={'RECOVERY':'Recovery（連線恢復）','POLLING':'Polling（連線訓練）','CONFIG':'連線設定'}.get(row.get('state_name'),'連線訓練')
        sequence.append(dict(label=label,packet_index=m['anchor']['packet_index']))
    return dict(headline=headline,observed=observed,uncertain=uncertain,next_check=next_check,
                meaning='這是已保留的流程核對入口，不是已確認的故障位置；單方向連線不代表整條連線正常。',
                resolved_evidence=resolved,missing_evidence=missing,
                primary_anchor=primary,followup_anchor=followup,sequence=sequence,
                action=dict(kind='NAVIGATE' if followup else 'EVIDENCE_REQUEST',
                            label='查看配置請求' if followup else '查看需補資料'),
                completion_note='全保留範圍的回覆數量不能代表此里程碑之後或同一裝置的回覆。')


def enrich_card(model,flow,scenario,card):
    view=build(model,flow,scenario)
    card['engineer_view']=view
    # Full action contracts stay available, but a prerequisite is not an actual gap.
    card['provenance_details']=copy.deepcopy(card['evidence_gaps'])
    card['evidence_gaps']=list(view['missing_evidence'])
    loc=card['locator'];card['navigation_locators']=[copy.deepcopy(loc)]
    if view['followup_anchor']:
        a=view['followup_anchor'];t=a.get('time_object')
        ns=t[0]*1000000000+t[1] if t and len(t)==3 and t[2]==0 else None
        card['navigation_locators'].append(dict(a,display_level=0,timestamp=dict(value=ns,unit='ns') if ns is not None else None))
        card['native_targets'].append(dict(protocol='PCIe',level=0,index=a['packet_index'],timestamp_ns=ns,channel=a['channel']))
    return card
