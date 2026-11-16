"""Trace-derived milestones, with explicit direction/epoch and claim ceilings.

Link Up is not L0; per-direction L0 is not device initialization. No file-name,
known failure time, golden Packet number or fixed-case pipeline is consulted.
"""
from bisect import bisect_right
import copy

FORMAT='pcie.stage-summary/v1'
CONFIG_TLP_TYPES=('0X9','0XA','0XB','0XC')


def location(value):
    if not value:return '位置尚未建立'
    time=value.get('time_object')
    if time and len(time)==3 and all(type(v) is int for v in time):
        stamp=str(time[0])+'.'+str(time[1]).zfill(9)+str(time[2]).zfill(3)+' s'
    elif time and len(time)>=2 and all(type(v) is int for v in time[:2]):
        stamp=str(time[0])+'.'+str(time[1]).zfill(9)+' s（ns 精度）'
    else:stamp=(value.get('time_display') or '時間未知')+'（原生顯示精度）'
    return 'Packet '+str(value['packet_index'])+' · '+str(value['direction'])+' · '+stamp


def anchor(row):
    return {k:copy.deepcopy(row.get(k)) for k in (
        'packet_index','time_display','time_object','time_precision','channel','direction',
        'epoch','link_identity','source_trace_sha256','display_trace_sha256','packet_namespace','evidence_ref')}


def summarize(phase, tlp_rows, binding, transactions=None):
    events=copy.deepcopy(phase['events']) if phase else []
    milestones=[];epochs={};boundaries={};current={};gaps=[]
    milestone_bytes=0
    def milestone(kind,row,explanation):
        nonlocal milestone_bytes
        item=dict(kind=kind,status='OBSERVED',explanation=explanation,anchor=anchor(row))
        import json
        import pcie_large_io
        milestone_bytes+=len(json.dumps(item,ensure_ascii=False).encode('utf-8'))
        if milestone_bytes>pcie_large_io.DEFAULTS['max_model_bytes']:
            raise pcie_large_io.ResourceLimit('階段摘要超過目前有界模型預算；完整 Config／TLP 證據仍在磁碟索引，不發布不完整分析。')
        milestones.append(item)
        return item
    for row in events:
        ch=row['channel'];epochs.setdefault(ch,0);boundaries.setdefault(ch,[])
        if row['kind']=='LINK' and row.get('semantic_status')=='VERSION_MAPPING_VERIFIED':
            semantic=row.get('semantic')
            if semantic in ('LINK_DOWN','LINK_UP'):
                # Each observed connection boundary clears that direction's
                # state. Epoch IDs are local observation intervals, not BDF or
                # physical-device identities and not paired across directions.
                epochs[ch]+=1;boundaries[ch].append(row['packet_index']);current.pop(ch,None)
                row['epoch']=epochs[ch]
                milestone(semantic+'_OBSERVED',row,'原生 Link 事件；操作是否預期需測試情境。')
        row['epoch']=epochs[ch]
        if row['kind']=='LTSSM':
            if row['valid']!=1 or row['direction']=='UNKNOWN' or row['state_name']=='UNKNOWN':
                current.pop(ch,None)
                gaps.append('Packet '+str(row['packet_index'])+' 的 LTSSM 有效性或方向不足，未作為完成里程碑。')
                continue
            state=row['state_name']
            if state in ('DETECT','HOT_RESET','DISABLED'):
                epochs[ch]+=1;boundaries[ch].append(row['packet_index']);row['epoch']=epochs[ch];current.pop(ch,None)
            if state in ('POLLING','CONFIG','RECOVERY'):
                milestone('TRAINING_OBSERVED',row,row['direction']+' 觀察到有效 '+state+'；不等於已進入 L0。')
            elif state=='L0':
                milestone('DIRECTION_L0_OBSERVED',row,row['direction']+' 觀察到有效 L0；不等於裝置初始化完成。')
            current[ch]=row
    # Input TLPs have already passed G1/G2 validation. They retain their source
    # precision. Do not synthesize exact timestamps from TimeToText output.
    configs=[]
    packet_transactions={r['index']:r for r in (transactions or {}).get('rows',[]) if r['namespace']=='packet'}
    for raw in tlp_rows:
        if raw.get('tlp_type_hex','').upper() not in CONFIG_TLP_TYPES: continue
        constants=phase['constants'] if phase else {}
        ch={'Upstream':constants.get('CHANNEL_1'),'Downstream':constants.get('CHANNEL_2')}.get(raw['channel'])
        row=dict(packet_index=raw['packet_index'],time_display=raw['time_display'],time_object=None,
                 time_precision='vendor_display_text_only',channel=ch,direction=raw['channel'] if raw['channel'] in ('Upstream','Downstream') else 'UNKNOWN',
                 epoch=bisect_right(boundaries.get(ch,[]),raw['packet_index']) if ch else None,
                 link_identity='UNKNOWN',source_trace_sha256=binding['source_trace_sha256'],
                 display_trace_sha256=binding['display_trace_sha256'],packet_namespace=binding['packet_namespace'],
                 evidence_ref=raw.get('evidence_ref'))
        tx=packet_transactions.get(raw['packet_index'])
        if tx:
            row.update(time_object=tx['time_object'],time_precision=tx['time_precision'],evidence_ref=tx['evidence_ref'])
        configs.append(milestone('CONFIG_REQUEST_OBSERVED',row,'已觀察到 Config Request；需核對相對應 Completion，不能視為初始化完成。'))
    # Stable packet ordering preserves idle -> packet samples at one index.
    # Alphabetic milestone names are not native event order.
    milestones.sort(key=lambda m:m['anchor']['packet_index'])
    last=milestones[-1] if milestones else None
    l0s=[m for m in milestones if m['kind']=='DIRECTION_L0_OBSERVED']
    last_l0=l0s[-1] if l0s else None
    # A historical L0 remains an observation, but cannot guide initialization
    # after a later disconnect, retraining, invalid sample, or unknown Link
    # event. With physical link pairing unknown, prefer the conservative
    # trace-wide boundary over reusing an older direction's success.
    if last_l0:
        l0_position=next(i for i in range(len(events)-1,-1,-1)
            if events[i]['packet_index']==last_l0['anchor']['packet_index']
            and events[i]['kind']=='LTSSM' and events[i].get('state_name')=='L0'
            and events[i].get('valid')==1)
        tail=events[l0_position+1:]
        if any(r['kind']=='LINK' or r['kind']=='LTSSM' and
               (r.get('valid')!=1 or r.get('state_name')!='L0' or r['direction']=='UNKNOWN') for r in tail):
            last_l0=None
            gaps.append('較早的 L0 後仍有 Link／Training 或無效狀態；不能沿用較早連線狀態推定目前初始化階段。')
    phase_truncated=phase and any(c['truncated'] for c in phase.get('coverage',[])
        if c['family'] in ('LTSSM_CHANGE','LINK_CONDITION'))
    if phase_truncated:
        last_l0=None
    recent_configs=[m for m in configs if not last_l0 or m['anchor']['packet_index']>last_l0['anchor']['packet_index']]
    checks=[]
    if last_l0:
        focus=last_l0['anchor']
        next_step='確認重新連線後的裝置初始化與 Config／Completion 證據'
        checks.append(dict(anchor=focus,text='從 Packet '+str(focus['packet_index'])+' 的有效 L0 往後核對 Config Request／Completion、目標 BDF 與擷取結尾；L0 本身不能證明裝置已辨識。'))
        if recent_configs:
            checks.append(dict(anchor=recent_configs[0]['anchor'],text='核對 L0 之後第一筆可見 Config Request 的目標、回覆狀態與是否存在資料缺口。'))
        else:
            gaps.append('最後一筆可見有效 L0 後，本次 TLP 訂閱未觀察到 Config Request；不能據此宣稱裝置沒有進行初始化。')
    elif last:
        focus=last['anchor'];next_step='確認後續有效 L0 與初始化證據'
        checks.append(dict(anchor=focus,text='先核對此位置之後的有效 LTSSM 與方向，再確認是否有 Config／Completion；不要把未觀察到當成已失敗。'))
    else:
        next_step='補足 Link／LTSSM 或 Config 的可追溯資料'
        checks.append(dict(anchor=None,text='目前沒有足夠來源建立流程階段；先檢查擷取範圍、過濾與所用解碼層。'))
    if not phase: gaps.append('本次只有 TLP 資料，沒有 Link／LTSSM 證據，不能重建 Hot Plug 流程。')
    if phase_truncated:
        gaps.append('Link／LTSSM 細節達上限，所列最後里程碑僅為已保留資料中的最後一筆。')
    gaps += ['全檔覆蓋與顯示過濾影響仍為 UNKNOWN；DONE 僅表示腳本完成。',
             '方向 epoch 為本次觀察區間；不同方向是否同一實體 Link／裝置尚未證明，不合併成雙向 L0 完成判定。',
             ('LTSSM VSE error-ignore mask='+str(phase['ltssm_ignore_settings']['nfm_ignore_errors'])+'（已讀回）；Flow Graph 設定需獨立核對，不宣稱兩者等價。' if phase and isinstance(phase.get('ltssm_ignore_settings'),dict) else 'LTSSM 使用原生預設 error-ignore 設定，尚未完成 Flow Graph 設定等價驗證。'),
             '沒有來源明確的測試情境，不把 Link Down 稱為預期 Hot Plug；沒有 SDE 身分或完成條件，不宣稱 SDE 初始化成功。']
    labels=dict(LINK_DOWN_OBSERVED='Link Down',LINK_UP_OBSERVED='Link Up',TRAINING_OBSERVED='Training',
                DIRECTION_L0_OBSERVED='單方向有效 L0',CONFIG_REQUEST_OBSERVED='Config Request')
    presentation=dict(headline='最後有證據的階段：'+(labels.get(last['kind'],last['kind']) if last else '尚未建立'),
        last_observation=(location(last['anchor'])+'\n'+last['explanation']) if last else '缺少可追溯里程碑；不能判斷初始化結果。',
        next_check=next_step+'\n'+'\n'.join(c['text'] for c in checks),
        claim_boundary='觀察到的階段，不是故障或初始化成功判定；全檔覆蓋 UNKNOWN。')
    return dict(format=FORMAT,source_trace_sha256=binding['source_trace_sha256'],display_trace_sha256=binding['display_trace_sha256'],
                packet_namespace=binding['packet_namespace'],observed_milestones=milestones,
                last_supported_milestone=last,next_unverified_step=next_step,
                recommended_checks=checks,coverage_and_limitations=list(dict.fromkeys(gaps)),
                hypotheses=[],product_policy='NOT_EVALUATED',device_initialization='NOT_ESTABLISHED',
                hot_plug_intent='UNKNOWN',bidirectional_l0='NOT_ESTABLISHED',
                direction_epochs={str(k):v for k,v in epochs.items()},events=events,presentation=presentation)
