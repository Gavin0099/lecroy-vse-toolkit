"""PCIe presentation boundary. Only the current, verified import may supply cards.

No USB engine or frozen W1-W5 case is imported here. Capture order is explicit;
this adapter does not add a fault rule, score, or nanosecond timestamp.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import uuid

import pcie_trace_import as importer
import native_navigation as nav
import pcie_event_coverage as event_coverage
import pcie_phase_evidence as phase_evidence
import pcie_transaction_evidence as transaction_evidence
import pcie_stage_summary as stage_summary
import pcie_detail_windows as detail_windows
import pcie_flow_triage as flow_triage

FORMAT = 'pcie-triage-inspection/v1'
SCOPE = 'PCIe TLP 關聯與鄰近 Message；未分析 DLLP／Link／ASPM 政策，無候選不代表 PCIe PASS。'
LIMITS = ['依擷取順序呈現，尚無經驗證的優先排序；不是根因機率。',
          'DONE 只表示擷取腳本完成，不代表全部協定或整份 trace 已通過檢查。',
          '擷取使用 ScriptForDisplayOnly；顯示過濾對訂閱的影響尚未核實。',
          '原生定位限工具自有工作階段；選單或主視圖讀回無法核對時，改用同一副本的 Ctrl+G。',
          '未載入 MUX、vendor register、ASPM 設定或固定案例的判定。']


def read(path):
    path=Path(path)
    if path.name=='fields.json' and path.parent.name=='verified-fields' and (path.parent.parent/'disk-index.json').exists():
        import pcie_disk_index
        return pcie_disk_index.Fields(path.parent.parent/'transactions.sqlite')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def checked(root, path, digest):
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or nav.digest(path) != str(digest).lower():
        raise ValueError('Evidence outside this import or SHA-256 mismatch: ' + str(path))
    return path


def compose(root, analysis_id):
    """Validate native receipt -> raw logs -> verifier -> G9 -> visible evidence."""
    root = Path(root).resolve()
    uuid.UUID(hex=analysis_id)
    request, worker, analysis = (read(root / n) for n in ('request.json', 'worker.json', 'analysis.json'))
    current = nav.verify_files(request)
    if current != worker.get('before') or worker.get('after') != current:
        raise ValueError('Native extraction does not describe the current source/display trace')
    if worker.get('status') not in ('ANALYSIS_COMPLETE', 'NO_TLP_OBSERVED'):
        raise ValueError('Incomplete native extraction cannot supply candidates')
    if not all(worker.get(k) is True for k in ('inputs_unchanged', 'working_unchanged', 'scripts_unchanged')):
        raise ValueError('Extraction integrity not established')
    work = root / 'display-working.pex'
    if nav.identity(work) != worker.get('working_after') or worker.get('working_before') != worker['working_after']:
        raise ValueError('Display copy changed after extraction')
    analysis_input = importer.extraction_input(request, worker, root)
    if 'analysis_input' in worker and worker['analysis_input'] != analysis_input:
        raise ValueError('Analysis input differs from sealed conversion evidence')
    import verify_g1a_log
    count = verify_g1a_log.check_log((root / 'count.txt').read_text(encoding='utf-8'))
    profile=request.get('extraction_profile','tlp-v1')
    if worker.get('extraction_profile','tlp-v1')!=profile:
        raise ValueError('Extraction profile differs from this request')
    selected=importer.selected_probes(request)
    expected = [n for n in selected
                if count['tlp_callback_count'] or n not in ('rows','fields','messages')]
    if [p['name'] for p in worker['probes']] != expected:
        raise ValueError('Extraction stages missing or duplicated')
    refs = []
    for p in worker['probes']:
        if p['finished']['result'] != 2:
            raise ValueError('VSE completion is partial')
        path = checked(root, root / (p['name'] + '.txt'), p['log_sha256'])
        refs.append({'path': str(path), 'sha256': nav.digest(path)})
    native_count = worker.get('native_packet_count')
    if native_count is not None and (type(native_count) is not int or native_count < 0):
        raise ValueError('Invalid native packet count')
    coverage = dict(native_packet_count=native_count, tlp_count=count['tlp_callback_count'],
                    first_tlp_index=count['first_tlp_index'], last_tlp_index=count['last_tlp_index'],
                    subscription='_PKT_TLP / _ANY_TYPE / all channels', range='natural trace traversal',
                    rows_cap=100000000, sampling=False, truncated=False,
                    subscription_complete=True, full_trace_coverage='UNKNOWN',
                    display_filter_effect='UNKNOWN',
                    excluded=['DLLP', 'ordered sets', 'Link conditions', 'electrical idle', 'vendor policy'],
                    done_meaning='VSE execution completion only')
    source_sha, display_sha = (analysis_input[k]['sha256'].lower() for k in ('source_trace', 'display_trace'))
    namespace = ('native_trace_packet_zero_based' if source_sha == display_sha
                 else 'converted_trace_packet_zero_based')
    binding = event_coverage.identity(analysis_id, source_sha, display_sha,
                                      worker.get('capabilities', {}).get('file_version'))
    coverage['event_families'] = [event_coverage.tlp_coverage(binding, count, refs)]
    coverage['capture_mode'] = 'UNKNOWN'
    coverage['zero_tlp_meaning'] = 'No callbacks in this Packet subscription; Flit or other event levels not excluded'
    phase=transactions=None
    if profile=='stage-v1':
        receipts={p['name']:p for p in worker['probes']}
        phase=phase_evidence.load(root,receipts['phase'],binding,native_count)
        transactions=transaction_evidence.load(root,receipts['transactions'],binding,native_count)
        if phase['counts']['TLP']['count']!=count['tlp_callback_count']:
            raise ValueError('Phase and independent TLP counters disagree')
        coverage['event_families'] += phase['coverage']+transactions['coverage']
        coverage['excluded']=['vendor policy','device initialization verdict','unobserved or filtered events']
        coverage['ltssm_ignore_settings']=phase['ltssm_ignore_settings']
        coverage['extraction_strategy']='existing TLP acquisition plus bounded phase and native transaction passes'
    findings, fields = [], []
    if count['tlp_callback_count']:
        manifest = read(root / 'triage-input.json')
        if manifest['trace']['sha256'].lower() != display_sha or manifest['trace']['tlp_count'] != count['tlp_callback_count']:
            raise ValueError('Triage manifest trace mismatch')
        if manifest.get('storage',{}).get('schema')=='pcie.disk-index/v1':
            from pcie_dense_analysis import validate_inputs
        else:
            from run_pcie_triage import validate_inputs
        validate_inputs(manifest, root)
        for name in ('fields', 'messages'):
            checked(root, manifest[name]['path'], manifest[name]['sha256'])
        run = read(root / 'report/run-manifest.json')
        checked(root, run['input_manifest']['path'], run['input_manifest']['sha256'])
        if Path(run['input_manifest']['path']).resolve() != root / 'triage-input.json' or run['status'] != 'PASS':
            raise ValueError('Report belongs to another import')
        path = checked(root, root / 'report/findings.json', run['package']['findings.json'])
        document = read(path)
        for entry in document['inputs'].values():
            checked(root, entry['path'], entry['sha256'])
        if Path(document['inputs']['fields']['path']).resolve() != Path(manifest['fields']['path']).resolve():
            raise ValueError('Finding fields do not match current import')
        fields = read(manifest['fields']['path'])
        field_summary = read(root / 'verified-fields/summary.json')
        if field_summary['log_sha256'].lower() != nav.digest(root / 'fields.txt'):
            raise ValueError('Field verifier is from another extraction')
        findings = document['findings']
        refs.extend([{'path': str(path), 'sha256': nav.digest(path)},
                     {'path': str(root / 'verified-fields/fields.json'), 'sha256': nav.digest(root / 'verified-fields/fields.json')}])
    elif analysis['findings_total'] != 0 or analysis['locators']:
        raise ValueError('Zero TLP extraction cannot supply candidates')
    by_index = fields.packet_map if hasattr(fields,'packet_map') else {r['packet_index']: r for r in fields}
    if transactions:transaction_evidence.validate_against_fields(transactions,fields)
    field_ref=dict(path=str(root/'verified-fields/fields.json'),sha256=nav.digest(root/'verified-fields/fields.json')) if fields else None
    stage_rows=fields.rows_of_types(int(t,16) for t in stage_summary.CONFIG_TLP_TYPES) if hasattr(fields,'rows_of_types') else fields
    summary=stage_summary.summarize(phase,(dict(r,evidence_ref=dict(**field_ref,row=r['row'])) for r in stage_rows),binding,transactions)
    tx_check=transaction_evidence.crosscheck(transactions,phase) if transactions else None
    if native_count is not None:
        for index in by_index: nav.validate_index(index, native_count)
    cards = []
    for finding in sorted(findings, key=lambda f: (f['where_to_look']['primary_go_to_packet'], f['finding_id'])):
        index = finding['where_to_look']['primary_go_to_packet']
        row = by_index[index]
        locator = dict(source_trace_sha256=source_sha, display_trace_sha256=display_sha,
                       packet_namespace=namespace, display_level=0, packet_index=index,
                       timestamp=None, time_display=row['time_display'], time_precision='vendor_display_text_only',
                       channel=row['channel'], direction=row['channel'] if row['channel'] in ('Upstream','Downstream') else 'UNKNOWN')
        matches = [p for p in analysis['locators'] if p['finding_id'] == finding['finding_id']]
        if len(matches) != 1 or any(matches[0].get(k) != v for k,v in locator.items()):
            raise ValueError('Candidate locator differs from verified extraction')
        nearby = sorted({a['packet'] for seg in finding['what_was_observed']['local_segments'] for a in seg['anchors']})
        if any(p not in by_index for p in nearby):
            raise ValueError('Missing candidate evidence row')
        context = [dict(index=p, time_display=by_index[p]['time_display'], timestamp_ns=None,
                        channel=by_index[p]['channel'], message=by_index[p]['tlp_type_hex'],
                        result=by_index[p]['compl_status'], detail=json.dumps(by_index[p],ensure_ascii=False),
                        evidence_ref=dict(path=str(root/'verified-fields/fields.json'),row=by_index[p]['row'])) for p in nearby]
        rank = len(cards) + 1
        cards.append(dict(rank=rank, protocol_rank=rank, protocol='PCIe',
            id=analysis_id+':'+finding['finding_id'], aggregation_key=finding['group_id'],
            title='TLP 關聯覆核 · Packet '+str(index), locator=locator,
            native_targets=[dict(protocol='PCIe',level=0,index=index,timestamp_ns=None,channel=row['channel'])],
            start_ns=None,end_ns=None,time_display=row['time_display'],time_precision='vendor_display_text_only',
            facts=[x['observed'] for x in finding['what_was_observed']['candidate_observations']],
            reasons=[x['surfaces'] for x in finding['why_surfaced']['detectors']],
            next_step='先在同一工作副本以 Ctrl+G 檢查 Packet '+str(index)+'，核對方向與 Tag／Requester ID；再看證據列中的後續封包與 Completion。先排除擷取缺口及交易結束，勿直接判定重送、Tag 違規或韌體故障。',
            evidence_gaps=finding['not_known']+['BDF/epoch/Link 狀態僅在有來源時才可判讀；本次未推定 epoch 或 vendor 設定生效。'],
            evidence_refs=refs, context=context, fact_vs_hypothesis='Observed association only; cause NOT_EVALUATED'))
    if len(cards) != analysis['findings_total']:
        raise ValueError('Candidate count differs from analysis')
    limits = list(LIMITS)
    if analysis.get('diagnostic_exports')=='on_demand':
        limits.append('完整 TLP 列與 Request／Completion 關聯已保存在 transactions.sqlite；附加列／角色／關聯 JSON 與 TSV 依需要匯出，未省略分析資料。')
        coverage['diagnostic_exports']='on_demand; complete index and canonical fields/messages retained'
    if worker.get('conversion', {}).get('status') == 'converted':
        limits.append('舊格式已由 PETracer 在工作副本自動轉換；原始檔未改動，Packet 編號屬於轉換後副本。')
    model = dict(format=FORMAT,analysis_id=analysis_id,protocol='pcie',trace_sha256=source_sha,
        source_trace_sha256=source_sha,display_trace_sha256=display_sha,display_trace_path=str(work),packet_namespace=namespace,
        rule_version='existing-g9/capture-order',run_status='complete' if cards else 'no_candidates',
        status='candidates_found' if cards else 'no_supported_candidate',scope=SCOPE,coverage=coverage,
        candidate_count_total=len(cards),episode_count=len(cards),omitted_episodes=max(0,len(cards)-3),
        sort_mode='capture_order',displayed_candidates=[c['id'] for c in cards[:3]],candidates=cards,observations=[],
        analyses=[dict(protocol='PCIe',state='analyzed',episode_count=len(cards),scope=SCOPE,coverage=coverage,limitations=limits)],
        analysis_stages=[dict(stage=p['name'],status='complete',elapsed_seconds=p.get('elapsed_seconds')) for p in worker['probes']],
        native_navigation='owned_menu_with_fallback' if native_count is not None else 'unavailable',limitations=limits,
        evidence_refs=refs)
    model['stage_summary']=summary
    model['transaction_crosscheck']=tx_check
    if request.get('detail_windows'):
        if not worker.get('native_details'):raise ValueError('Requested native details have no receipt')
        detail_binding={k:model[k] for k in ('source_trace_sha256','display_trace_sha256','packet_namespace')}
        expected=detail_windows.propose(analysis['locators'],summary,native_count)
        detail=detail_windows.load(root,worker['native_details'],detail_binding,expected)
        model['native_details']=detail
        for c in cards:
            matches=[w for w in detail['windows'] if any(a['reason']=='candidate' and a['packet_index']==c['locator']['packet_index'] for a in w['anchors'])]
            context_by_index={r['index']:r for r in c['context']}
            for w in matches:
                for r in w.get('rows',[]):
                    existing=context_by_index.get(r['packet_index'])
                    if existing is not None:
                        existing.update(native_text=r['native_text'],native_evidence_ref=r['evidence_ref'],native_timestamp_seconds=r['timestamp_seconds'])
                        continue
                    context_by_index[r['packet_index']]=dict(index=r['packet_index'],time_display=(r['timestamp_seconds']+' s') if r['timestamp_seconds'] else 'UNKNOWN',
                        timestamp_ns=None,channel=r['direction'],message='原生區間明細',result='觀察，非故障判定',
                        detail=r['native_text'],evidence_ref=r['evidence_ref'])
            c['context']=[context_by_index[i] for i in sorted(context_by_index)]
            c['evidence_gaps'].append('鄰近原生明細僅涵蓋明示 Packet 區間；過濾與區間外資料仍未知。')
        if detail['status']=='partial':model['limitations'].append('部分原生區間明細未取得；既有候選保留，不能以缺列推定封包不存在。')
    last=summary.get('last_supported_milestone')
    if last:
        a=last['anchor'];t=a.get('time_object')
        ns=t[0]*1000000000+t[1] if t and all(v is not None for v in t) and t[2]==0 else None
        locator=dict(a,display_level=0,timestamp=dict(value=ns,unit='ns') if ns is not None else None)
        context=[]
        for w in model.get('native_details',{}).get('windows',[]):
            if any(x['reason']=='last_supported_milestone' and x['packet_index']==a['packet_index'] for x in w['anchors']):
                context+=[dict(index=r['packet_index'],time_display=(r['timestamp_seconds']+' s') if r['timestamp_seconds'] else 'UNKNOWN',
                    timestamp_ns=None,channel=r['direction'],message='階段附近原生明細',result='觀察，非故障判定',detail=r['native_text'],evidence_ref=r['evidence_ref']) for r in w['rows']]
        model['observations']=[dict(rank=1,protocol_rank=1,protocol='PCIe',id=analysis_id+':last-stage',
            title=summary['presentation']['headline'],locator=locator,
            native_targets=[dict(protocol='PCIe',level=0,index=a['packet_index'],timestamp_ns=ns,channel=a['channel'])],
            start_ns=ns,end_ns=ns,time_display=a['time_display'],time_precision=a['time_precision'],
            facts=[summary['presentation']['last_observation']],reasons=['本次來源中的最後可見階段；不是故障候選。'],
            next_step=summary['presentation']['next_check'],evidence_gaps=summary['coverage_and_limitations'],
            context=context,evidence_refs=[a['evidence_ref']])]
    if phase:
        scope='PCIe TLP 關聯、Link／LTSSM 階段及有上限的 DLLP／原生交易觀察；未判定 ASPM 政策或裝置初始化成功，無候選不代表 PCIe PASS。'
        model['scope']=scope
        model['analyses'][0]['scope']=scope
    model['flow_transaction_evidence']=transactions
    flow_triage.attach(model,transactions)
    return validate(model)


def validate(model):
    if model.get('external_model'):
        import pcie_model_storage
        validate(pcie_model_storage.expand(model))
        return model
    if model.get('format') != FORMAT or model.get('sort_mode') != 'capture_order':
        raise ValueError('Unsupported PCIe presentation contract')
    uuid.UUID(hex=model['analysis_id'])
    if model['trace_sha256'] != model['source_trace_sha256'] or len(model['trace_sha256']) != 64:
        raise ValueError('Invalid source identity')
    summary=model.get('stage_summary')
    if summary is not None:
        if summary.get('format')!=stage_summary.FORMAT or any(summary.get(k)!=model[k] for k in ('source_trace_sha256','display_trace_sha256','packet_namespace')):
            raise ValueError('Stage summary belongs to another source')
        for m in summary['observed_milestones']+summary['recommended_checks']:
            a=m['anchor']
            if a is None:continue
            if any(a.get(k)!=model[k] for k in ('source_trace_sha256','display_trace_sha256','packet_namespace')) or not a.get('evidence_ref'):
                raise ValueError('Stage anchor source mismatch')
            if model['coverage']['native_packet_count'] is not None:nav.validate_index(a['packet_index'],model['coverage']['native_packet_count'])
    cards = model['candidates']
    for observation in model.get('observations',[]):
        loc=observation['locator']
        nav.validate_request(dict(schema='pcie.navigation-probe/v1',source_trace=dict(path=model['display_trace_path'],sha256=model['source_trace_sha256']),display_trace=dict(path=model['display_trace_path'],sha256=model['display_trace_sha256']),anchors=[loc]))
        if loc['packet_index']!=summary['last_supported_milestone']['anchor']['packet_index'] or observation['native_targets'][0]['index']!=loc['packet_index']:
            raise ValueError('Stage navigation differs from current evidence')
    if len(cards) != model['candidate_count_total'] or len(cards) != model['episode_count']:
        raise ValueError('Invalid candidate total')
    seen = set()
    previous = -1
    for i,c in enumerate(cards,1):
        loc=c['locator']
        request=dict(schema='pcie.navigation-probe/v1',source_trace=dict(path=model['display_trace_path'],sha256=model['source_trace_sha256']),
                     display_trace=dict(path=model['display_trace_path'],sha256=model['display_trace_sha256']),anchors=[loc])
        nav.validate_request(request)
        if c['id'] in seen or not c['id'].startswith(model['analysis_id']+':') or c['rank'] != i or c['protocol'] != 'PCIe':
            raise ValueError('Stale or duplicate candidate identity')
        if c['native_targets'][0]['index'] != loc['packet_index'] or loc['packet_namespace'] != model['packet_namespace']:
            raise ValueError('Native target identity mismatch')
        if loc['packet_index'] < previous or c['start_ns'] is not None or not c['evidence_refs']:
            raise ValueError('Invalid capture order, time precision or evidence')
        seen.add(c['id']);previous=loc['packet_index']
    if 'flow_analysis' in model:
        flow=model['flow_analysis']
        if flow!=flow_triage.build(model,model.get('flow_transaction_evidence'),flow.get('expected_context')):
            raise ValueError('Flow analysis differs from current source, context or knowledge pack')
        if model.get('flow_items')!=flow_triage.cards(model,flow):raise ValueError('Flow navigation differs from source evidence')
        if model.get('engineer_view')!=flow_triage.engineer.build(model,flow):raise ValueError('Engineering summary differs from source evidence')
        for item in model['flow_items']:
            for loc in item.get('navigation_locators',[item['locator']]):
                nav.validate_request(dict(schema='pcie.navigation-probe/v1',source_trace=dict(path=model['display_trace_path'],sha256=model['source_trace_sha256']),display_trace=dict(path=model['display_trace_path'],sha256=model['display_trace_sha256']),anchors=[loc]))
                if model['coverage']['native_packet_count'] is not None:nav.validate_index(loc['packet_index'],model['coverage']['native_packet_count'])
    return model


def with_context(model,context):
    import copy
    external=bool(model.get('external_model'))
    if external:
        import pcie_model_storage
        model=pcie_model_storage.expand(model)
    validate(model)
    result=copy.deepcopy(model)
    flow_triage.attach(result,result.get('flow_transaction_evidence'),context)
    result=validate(result)
    return pcie_model_storage.pack(result,Path(result['display_trace_path']).parent) if external else result


def markdown_full(model):
    validate(model)
    lines=['# PCIe Trace 檢查工作區',model['scope'],
           '排序：依擷取順序（不是優先程度或根因機率）。候選總數：'+str(model['candidate_count_total']),
           'Source SHA-256: '+model['source_trace_sha256'], 'Display SHA-256: '+model['display_trace_sha256'],
           'Display: '+model['display_trace_path'], 'Namespace: '+model['packet_namespace'],
           ]
    if model.get('flow_analysis'):
        f=model['flow_analysis'];p=f['presentation']
        lines+=['## '+p['headline'],p['context'],p['observed'],'### 為什麼先核對',p['why_inspect'],'### 下一步',p['next_check'],p['claim_boundary'],p['packet_summary']]
        for e in sorted(f['scenarios'],key=lambda x:f['priority_order'].index(x['scenario_id'])):
            lines+=['### '+e['title'],str(e['link_scope']),*e['what_observed'],e['why_inspect'],*[a['text'] for a in e['next_actions']],*e['remaining_unknowns']]
            for action in e['next_actions']:
                lines+=['#### 建議來源與適用範圍：'+action['action_id'],*flow_triage.actions.describe(action)]
            lines += [c['rule_id']+' · '+c['source_kind']+' · '+c['source_url']+' · '+c['explanation'] for c in e['applicable_cards']]
        lines+=['### Completion 與來源核對（不是完整配對）',p['completion_summary'],'```json',json.dumps(f['transaction_checks'],ensure_ascii=False,indent=2),'```']
    elif model.get('stage_summary'):
        s=model['stage_summary'];p=s['presentation']
        lines+=['## '+p['headline'],p['last_observation'],'### 下一個待核對步驟',p['next_check'],p['claim_boundary'],
                '### 階段證據與限制',*s['coverage_and_limitations'],'```json',json.dumps(s,ensure_ascii=False,indent=2),'```']
    lines+=['## 擷取範圍','```json',json.dumps(model['coverage'],ensure_ascii=False,indent=2),'```']
    if model.get('transaction_crosscheck') is not None:
        lines+=['## 原生交易核對（不是根因判定）','```json',json.dumps(model['transaction_crosscheck'],ensure_ascii=False,indent=2),'```']
    if model.get('native_details') is not None:
        lines+=['## 原生區間明細（僅匯出列，不代表全檔覆蓋）','```json',json.dumps(model['native_details'],ensure_ascii=False,indent=2),'```']
    if not model['candidates']:lines.append('本次範圍內沒有候選；不代表 PCIe PASS。')
    for c in model['candidates']:
        lines += ['## '+c['title'],c['time_display']+' · '+str(c['locator']['direction']),
                  '### 下一步',c['next_step'],'### 觀察事實',*c['facts'],'### 列出原因',*c['reasons'],
                  '### 證據與限制',*c['evidence_gaps'],'```json',json.dumps(c['context'],ensure_ascii=False,indent=2),'```',
                  '來源參照：',*[r['path']+' · SHA-256 '+r['sha256'] for r in c['evidence_refs']]]
    if model.get('external_model'):
        job=Path(model['display_trace_path']).parent.parent
        lines+=['## 完整分檔證據',*['['+'/'.join(r['keys'])+']('+Path(r['path']).relative_to(job).as_posix()+') · SHA-256 '+r['sha256'] for r in model['external_model']['refs']]]
    return '\n\n'.join(lines+['## 本次限制',*model['limitations']])+'\n'


def render_full(model):
    validate(model)
    esc=lambda value:html.escape(str(value))
    lines=lambda values:'<ul>'+''.join('<li>'+esc(v)+'</li>' for v in values)+'</ul>'
    body=('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>PCIe Trace 檢查工作區</title>'
          '<style>body{background:#f5f5f5;color:#242424;font:16px system-ui;margin:24px}main{max-width:1100px;margin:auto}section,article{background:white;padding:24px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}summary:focus-visible{outline:2px solid #0f6cbd}</style><main>'
          '<h1>PCIe Trace 檢查工作區</h1><p>'+esc(model['scope'])+'</p><p>依擷取順序（不是優先程度或根因機率） · 候選總數 '+str(model['candidate_count_total'])+'</p>')
    coverage=model['coverage']
    if model.get('flow_analysis'):
        f=model['flow_analysis'];p=f['presentation']
        body+='<section><h2>'+esc(p['headline'])+'</h2><p>'+esc(p['context'])+'</p><p>'+esc(p['observed']).replace('\n','<br>')+'</p><h3>為什麼先核對</h3><p>'+esc(p['why_inspect'])+'</p><h3>下一步</h3><p>'+esc(p['next_check'])+'</p><p>'+esc(p['claim_boundary'])+'</p><p>'+esc(p['packet_summary'])+'</p></section>'
        for e in sorted(f['scenarios'],key=lambda x:f['priority_order'].index(x['scenario_id'])):
            body+='<section><details><summary>'+esc(e['output_class']+' · '+e['title']+' · '+stage_summary.location(e['focus_anchor']))+'</summary>'+lines(e['what_observed'])+'<p>'+esc(e['why_inspect'])+'</p>'+lines([a['text'] for a in e['next_actions']])+lines(e['remaining_unknowns'])
            for action in e['next_actions']:
                body+='<details><summary>建議來源與適用範圍：'+esc(action['action_id'])+'</summary>'+lines(flow_triage.actions.describe(action))+'</details>'
            body+='<h3>觀察與情境</h3>'+lines([o['output_class']+' · '+o.get('interpretation',o['explanation']) for o in e['observations']])
            body+='<h3>知識來源（工程提示，非規範違規）</h3>'+lines([c['rule_id']+' · '+c['source_kind']+' · '+c['explanation'] for c in e['applicable_cards']])
            for c in e['applicable_cards']:body+='<p><a href="'+esc(c['source_url'])+'">'+esc(c['rule_id']+' · '+c['revision_or_commit'])+'</a></p>'
            body+='</details></section>'
        body+='<section><h2>可見 Completion</h2><p>'+esc(p['completion_summary'])+'</p><details><summary>狀態、關聯層級與來源（不是完整配對）</summary><pre>'+esc(json.dumps(f['transaction_checks'],ensure_ascii=False,indent=2))+'</pre></details></section>'
    elif model.get('stage_summary'):
        s=model['stage_summary'];p=s['presentation']
        body+='<section><h2>'+esc(p['headline'])+'</h2><p>'+esc(p['last_observation']).replace('\n','<br>')+'</p><h3>下一個待核對步驟</h3><p>'+esc(p['next_check']).replace('\n','<br>')+'</p><p>'+esc(p['claim_boundary'])+'</p>'
        body+='<details><summary>階段事件鏈、來源與限制</summary>'+lines(s['coverage_and_limitations'])+'<pre>'+esc(json.dumps(s,ensure_ascii=False,indent=2))+'</pre></details></section>'
    body+='<section><h2>擷取範圍</h2><p>原生 Packet 總數：'+esc(coverage['native_packet_count'])+'；本次 TLP：'+esc(coverage['tlp_count'])+'</p>'+lines(model['limitations'])
    body+='<details><summary>來源、工作副本與詳細範圍</summary><pre>'+esc(json.dumps({k:model[k] for k in ('analysis_id','source_trace_sha256','display_trace_sha256','display_trace_path','packet_namespace','coverage')},ensure_ascii=False,indent=2))+'</pre></details></section>'
    if model.get('transaction_crosscheck') is not None:
        body+='<section><details><summary>原生交易核對（不是根因判定）</summary><pre>'+esc(json.dumps(model['transaction_crosscheck'],ensure_ascii=False,indent=2))+'</pre></details></section>'
    if model.get('native_details') is not None:
        body+='<section><details><summary>原生區間明細（僅匯出列，不代表全檔覆蓋）</summary><pre>'+esc(json.dumps(model['native_details'],ensure_ascii=False,indent=2))+'</pre></details></section>'
    if not model['candidates']:body+='<section>本次範圍內沒有候選；不代表 PCIe PASS。</section>'
    for c in model['candidates']:
        body+='<article><h2>'+esc(c['title'])+'</h2><p>'+esc(c['time_display'])+' · '+esc(c['locator']['direction'])+'</p><h3>下一步</h3><p>'+esc(c['next_step'])+'</p><h3>觀察事實</h3>'+lines(c['facts'])+'<h3>列出原因</h3>'+lines(c['reasons'])
        body+='<details><summary>前後封包、證據來源與限制</summary>'+lines(c['evidence_gaps'])+'<pre>'+esc(json.dumps(dict(context=c['context'],evidence_refs=c['evidence_refs']),ensure_ascii=False,indent=2))+'</pre></details></article>'
    if model.get('external_model'):
        job=Path(model['display_trace_path']).parent.parent
        body+='<section><h2>完整分檔證據</h2><p>摘要未載入完整陣列，不代表未觀察到事件。附件保留完整已擷取內容。</p><ul>'
        for r in model['external_model']['refs']:
            link=Path(r['path']).relative_to(job).as_posix()
            body+='<li><a href="'+esc(link)+'">'+esc(' / '.join(r['keys']))+'</a> · '+esc(r['bytes'])+' bytes · SHA-256 '+esc(r['sha256'])+'</li>'
        body+='</ul></section>'
    return body+'</main></html>'


def markdown(model):
    """Three reading levels; retain the complete previous report verbatim."""
    complete=markdown_full(model)
    if not model.get('engineer_view'):return complete
    p=model['engineer_view']
    lines=['# '+p['headline'],'## 目前確認了什麼',p['observed'],
           '## 哪裡仍有疑問',p['uncertain'],'## 下一步核對',p['next_check'],p['meaning'],
           '<details><summary>事件順序與下一步所需資料</summary>','',
           ' → '.join(s['label']+' · Packet '+str(s['packet_index']) for s in p['sequence']),
           '### 本次仍需的證據',*p['missing_evidence'],p['completion_note'],
           '交易觀察 '+str(model['candidate_count_total'])+' 筆，保留獨立定位；不直接視為同一故障。',
           '</details>','', '<details><summary>進階證據、完整報告與來源</summary>','',
           complete,'</details>']
    return '\n\n'.join(lines)+'\n'


def render(model):
    complete=render_full(model)
    if not model.get('engineer_view'):return complete
    p=model['engineer_view'];esc=lambda value:html.escape(str(value),quote=True)
    lines=lambda xs:'<ul>'+''.join('<li>'+esc(x)+'</li>' for x in xs)+'</ul>'
    # The complete source report stays nested, rather than inserting another HTML document.
    advanced=complete.split('<main>',1)[1].rsplit('</main>',1)[0]
    label='查看配置請求 Packet '+str(p['followup_anchor']['packet_index']) if p['followup_anchor'] else '查看需補資料'
    sequence=' → '.join(s['label']+' · Packet '+str(s['packet_index']) for s in p['sequence']) or '尚無可追溯事件順序'
    body='''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PCIe 工程檢查摘要</title>
<style>body{background:#f5f5f5;color:#242424;font:16px/1.65 system-ui,"Microsoft JhengHei";margin:24px}main{max-width:1060px;margin:auto}section,article{background:white;padding:22px;margin:16px 0;border:1px solid #dedede;border-radius:8px}h1{font-size:27px;line-height:1.4}h2{font-size:18px;margin:16px 0 4px}p{margin:6px 0}summary{cursor:pointer;font-weight:600;padding:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}button,a{font:inherit}button{background:#0f6cbd;color:white;border:0;border-radius:5px;padding:10px 16px;cursor:pointer}a{color:#0f6cbd}:focus-visible{outline:3px solid #0f6cbd;outline-offset:3px}.muted{color:#475569}.boundary{border-left:3px solid #475569;padding-left:12px}details details{margin-left:12px}</style></head><body><main>'''
    body+='<p class="muted">PCIe · 工程檢查摘要</p><h1>'+esc(p['headline'])+'</h1><section id="first-screen"><h2>目前確認了什麼</h2><p>'+esc(p['observed'])+'</p><h2>哪裡仍有疑問</h2><p>'+esc(p['uncertain'])+'</p><h2>下一步核對</h2><p>'+esc(p['next_check'])+'</p><p class="boundary">'+esc(p['meaning'])+'</p><button type="button" id="next-check">'+esc(label)+'</button><p class="muted">另有 '+str(model['candidate_count_total'])+' 筆交易觀察，保留獨立定位；不直接當成同一故障。</p></section>'
    body+='<section><details id="events"><summary>事件順序與下一步所需資料</summary><p>'+esc(sequence)+'</p><h2>本次仍需的證據</h2>'+lines(p['missing_evidence'])+'<p>'+esc(p['completion_note'])+'</p>'
    if p['followup_anchor']:body+='<p>下一個可核對位置：'+esc(flow_triage.engineer.location(p['followup_anchor']))+'。桌面工具可直接定位；離線報告請使用同一工作副本核對此編號。</p>'
    body+='</details></section><section><details id="advanced"><summary>進階證據、完整報告與來源</summary>'+advanced+'</details></section>'
    return body+'''</main><script>document.getElementById('next-check').addEventListener('click',()=>{const e=document.getElementById('events');e.open=true;e.querySelector('summary').focus();e.scrollIntoView({block:'start'});});</script></body></html>'''
