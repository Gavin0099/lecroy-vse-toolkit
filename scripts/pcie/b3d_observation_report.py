#!/usr/bin/env python3
"""W4+W5: Markdown and offline HTML from source-recomputed typed observations."""
from __future__ import annotations
import argparse
import html
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote
import b3a_event_contract as contract
import b3b_unified_timeline as adapter


def build_model(doc, root):
    """Use defined observation/source fields only; never interpret opaque prose."""
    raw=contract.load_sources(doc,root); contract.validate(doc,raw)
    data={k:json.loads(v) for k,v in raw.items()}
    evaluation, findings=data['evaluation'],data['findings']
    rules=[]
    for i,r in enumerate(evaluation['evaluations']):
        rules.append({'id':r['rule_id'],'title':findings['findings'][i]['title'],
                      'status':r['status'],'summary':r['summary'],'limitation':r['limitation'],
                      'evidence':[contract.evidence('evaluation',f'/evaluations/{i}')] +
                                 [contract.evidence('training',e['source']) for e in r['evidence']]})
    returns={}
    for event in doc['events']:
        for c in event['details'].get('config_completions',[]):
            if c['read_return_observation'] is not None:
                returns.setdefault(c['access_id'],[]).append({'packet':event['packet_index'],'value':c['read_return_observation']})
    config=[]; link=[]
    for event in doc['events']:
        q=event['details'].get('config_request')
        if q:
            config.append({'packet':event['packet_index'],'time':event['time_display'],'epoch':event['device_epoch'],
                'type':q['type'],'bdf':q['target_bdf'],'offset':q['register_byte_offset'],
                'first_be':q['first_be'],'last_be':q['last_be'],'write_intent':q['write_value'],
                'returns_at_completion':returns.get(q['access_id'],[]), 'completion_packets':q['completion_packets'],
                'association_outcome':q['association_outcome'],'value_status':q['value_status'],'evidence':event['evidence']})
        if event['layer']!='TLP':
            link.append({'packet':event['packet_index'],'time':event['time_display'],'direction':event['direction'],
                         'kind':event['kind'],'record':event['details']['link_record'],'evidence':event['evidence']})
    intents=[{'observation':r,'evidence':[contract.evidence('watchlist',f'/observations/{i}')]} for i,r in enumerate(data['watchlist']['observations'])]
    return {'schema':'pcie.observation-report/v1','title':'PCIe 切換後觀察報告',
        'capture_sha256':doc['capture_sha256'],'trace':evaluation['product_context']['case']['trace_basename'],
        'focus':findings['investigation_focus'],'focus_evidence':[contract.evidence('findings','/investigation_focus')],
        'case':evaluation['product_context']['case'],'case_evidence':[contract.evidence('evaluation','/product_context/case')],
        'metrics':{'packet_observations':len(doc['events']),'distinct_packet_anchors':len({r['packet_index'] for r in doc['events']}),
                   'config_requests':len(config),'observed_read_returns':sum(len(v) for v in returns.values()),
                   'interval_summaries':len(doc['intervals']),'has_errors':sum(r['counts']['err_any'] for r in doc['intervals'])},
        'rules':rules,'intents':intents,'config':config,'link':link,'intervals':doc['intervals'],'gaps':doc['gaps'],
        'observations':evaluation['observations'],'observation_evidence':[contract.evidence('evaluation','/observations')],
        'validation_debt':evaluation['validation_debt'],'debt_evidence':[contract.evidence('evaluation','/validation_debt')],
        'coverage':doc['coverage'],'limitations':doc['limitations'],'sources':doc['sources'],
        'next_evidence':findings['investigation_focus']['next_evidence']}


def value(v):
    return 'UNKNOWN' if v is None else f'0x{v:X}'


def md(text):
    text=html.escape(str(text),quote=False).replace('\r',' ').replace('\n',' ')
    for char in '\\`|[]()*_#!':text=text.replace(char,'\\'+char)
    return text


def source_link(model, ref, prefix):
    path=prefix.rstrip('/')+'/'+model['sources'][ref['source_id']]['path']
    return quote(path,safe='/')+'#'+quote(ref['json_pointer'],safe='')


def refs_md(model, refs, prefix):
    return '; '.join(f"[{md(r['source_id']+':'+r['json_pointer'])}]({source_link(model,r,prefix)})" for r in refs)


def refs_html(model, refs, prefix):
    return ' · '.join(f'<a href="{html.escape(source_link(model,r,prefix),quote=True)}">{html.escape(r["source_id"]+":"+r["json_pointer"])}</a>' for r in refs)


def link_description(row):
    r=row['record']
    if row['kind']=='ltssm':return f"{r['state_name']} / {r.get('substate_name','UNKNOWN')} ; valid={r['valid']}"
    if row['kind']=='link_condition':return r['type_name']
    if row['kind']=='nak':return f"NAK seq={r['seq']}（不推定 replay）"
    return f"raw speed code={r['speed']}, width={r['width']}（不自行換算速率）"


def render_markdown(m, prefix):
    refs=lambda rows:refs_md(m,rows,prefix)
    stats=m['metrics']; case=m['case']
    lines=[f"# {m['title']}",'',md(m['trace']),f"Capture SHA-256: {m['capture_sha256']}",'',
           md(m['focus']['question']),md(m['focus']['limitation']),refs(m['focus_evidence']),'',
           '## 工程師回報與觀察邊界','',
           f"Ground truth: {md(case['reported_outcome'])}（工程師回報，非 trace 自動判定）。",md(case['reported_symptom']),
           f"Crash dump verified: {case['crash_dump_verified']}；其他測試的 {md(', '.join(case['other_tests_bsod']))} 不當成本 capture 的 stop code。",refs(m['case_evidence']),'',
           'B1d COMPLETE；B2g product policy 仍 SOURCE_SCOPE_GATE；B2h conditional。沒有建立 BSOD root cause。','',
           '## Coverage','',f"{stats['packet_observations']} observations / {stats['distinct_packet_anchors']} distinct packet anchors；這不是 capture packet 總數。",
           f"{stats['config_requests']} config requests / {stats['observed_read_returns']} observed read returns / {stats['interval_summaries']} interval summaries / {stats['has_errors']:,} HasErrors。",'']
    lines += [f'- {md(x)}' for x in m['coverage']]
    lines += ['',f"雙向 L0 到尾端 display-time 差：{m['observations']['post_l0_observed_seconds']} sec；顯示時間無差不代表物理時間為零。 {refs(m['observation_evidence'])}"]
    lines += ['', '## 既有里程碑與產品規則','', '| 項目 | Status | 觀察／解讀 | Evidence |','| --- | --- | --- | --- |']
    for r in m['rules']:lines.append(f"| {md(r['id'])} | {r['status']} | {md(r['summary'])} | {refs(r['evidence'][:1])} |")
    for r in m['rules']:lines += ['',f"### {md(r['title'])}：{r['status']}",'',md(r['limitation']),refs(r['evidence'])]
    lines += ['', '## LinkControl write intent','', '| Packet | Time | Epoch / BDF | Write intent | ASPM intent | Effective / Expected / Policy | Evidence |', '| --- | --- | --- | --- | --- | --- | --- |']
    for item in m['intents']:
        r=item['observation'];lines.append(f"| {r['packet_index']} | {r['time_display']} | {md(r['epoch'])} / {r['bdf']} | {value(r['observed_write_intent'])} | {md(r['observation_kind'])} / {r['aspm_control_intent']} | {r['effective_state']} / {r['expected_state']} / {r['policy_result']} | {refs(item['evidence'])} |")
    lines += ['', 'Write＋Completion 不是 applied register state／System ASPM／Disable ASPM violation；四組工程師規則尚未提供。','', '## Link / DLLP 逐筆觀察','', '| Packet | Display time | Direction | Observation | Evidence |','| --- | --- | --- | --- | --- |']
    for r in m['link']:lines.append(f"| {r['packet']} | {r['time']} | {r['direction']} | {md(link_description(r))} | {refs(r['evidence'])} |")
    lines += ['', '## 未觀察區間與 sample 限制','']
    for g in m['gaps']:lines += [f"- {g['after_time']}..{g['before_time']}：{g['display_duration_seconds']} sec（display-time 差）；packet {g['after_index']} 與 {g['before_index']} 之間，沒有虛構 packet，也不證明電氣靜默。 {refs(g['evidence'])}"]
    samples=sum(len(r['details']['gui_samples']) for r in m['intervals'])
    lines += ['',f"{len(m['intervals'])} 個 segment 的 TS／DLLP 計數是區間摘要。GUI TS error 只抽樣 {samples} 筆；各筆 sample 沒有來源 timestamp，不能用區間端點補時間。",'',
              '| Packet interval | Display time | Events | HasErrors | Category counts | Evidence |',
              '| --- | --- | --- | --- | --- | --- |']
    for r in m['intervals']:
        lines.append(f"| {r['first_index']}..{r['last_index']} | {r['first_time']}..{r['last_time']} | {r['counts']['events']:,} | {r['counts']['err_any']:,} | {md(json.dumps(r['counts'],ensure_ascii=False,sort_keys=True))} | {refs(r['evidence'])} |")
    lines += ['','### GUI samples','']
    for r in m['intervals']:
        for s in r['details']['gui_samples']:
            sample=s['sample']
            lines.append(f"- GUI sample Packet {sample['packet_index']}：{md(', '.join(sample['gui_error_labels']))}；{md(sample['speed'])} GT/s {md(sample['width'])}；Time UNKNOWN（僅代表此 sample）。 {refs(s['evidence'])}")
    lines += ['', '## RC config request / Completion','',
              'Read return 顯示在 Completion packet；Write DWORD 是 BE 選擇的意圖，不是有效狀態。缺 Completion 不判 timeout。','',
              '| Packet | Time | Epoch / BDF | Type / Offset | BE | Write DWORD intent | Read return @ Completion | Association / Cpl packets | Evidence |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in m['config']:
        ret=', '.join(f"{value(c['value'])} @ {c['packet']}" for c in r['returns_at_completion']) or 'UNKNOWN'
        lines.append(f"| {r['packet']} | {r['time']} | {md(r['epoch'])} / {r['bdf']} | {r['type']} / {value(r['offset'])} | {value(r['first_be'])}/{value(r['last_be'])} | {value(r['write_intent'])} | {ret} | {md(r['association_outcome'])} / {md(r['completion_packets'])} | {refs(r['evidence'])} |")
    lines += ['', '## 後續 capture 需要的證據','']+[f'- {md(x)}' for x in m['next_evidence']]
    lines += ['- 對應 OS 裝置可見性、driver／emulation log 與 crash dump；目前未驗證 crash dump。','', '## Validation debt（不阻擋 B1d）','']
    lines += [f"- {md(d['id'])}: {d['status']}；{md(d['reason'])}" for d in m['validation_debt']]
    lines += [refs(m['debt_evidence']),'','## 限制','']+[f'- {md(x)}' for x in m['limitations']]
    lines += ['','## Source registry','', '| Source | Binding | SHA-256 |','| --- | --- | --- |']
    for key,src in m['sources'].items():lines.append(f"| {refs([contract.evidence(key,'')])} | {src['binding']} | {src['sha256']} |")
    return '\n'.join(lines)+'\n'


CSS='''body{margin:0;background:#f3f6fa;color:#182638;font:16px/1.6 system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1250px;margin:auto;padding:32px}.capture{font:12px/1.5 Consolas,monospace;overflow-wrap:anywhere}header{background:#163955;color:white;border-radius:18px;padding:30px}h1{font-size:32px;margin:0 0 10px}h2{margin-top:38px}h3{margin:0}a{color:#1b6088;overflow-wrap:anywhere}nav{display:flex;flex-wrap:wrap;gap:20px;padding:20px 0}.card,details{background:white;border:1px solid #d8e1ec;border-radius:12px;padding:18px;margin:12px 0}summary{cursor:pointer;font-weight:650}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.stat{background:white;border-radius:12px;padding:16px}.stat b{font-size:28px;display:block}.muted{color:#526479;font-size:14px}.badge{display:inline-block;padding:2px 9px;border-radius:8px;background:#e6ecf2;font-size:13px;font-weight:700;margin-left:8px}.PASS{background:#d6efdf;color:#145235}.FAIL{background:#fbe0dd;color:#922b24}.INCONCLUSIVE{background:#fff0c9;color:#745315}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;background:white;font-size:14px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #dde5ee;padding:10px}th{background:#e9f0f7}code,pre{font-family:Consolas,monospace}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;background:#f5f8fb;padding:12px}section{scroll-margin-top:15px}.source{font-size:12px;margin-top:9px}footer{padding:25px 0;color:#526479}@media(max-width:750px){main{padding:16px}header{padding:20px}.stats{grid-template-columns:repeat(2,1fr)}h1{font-size:25px}}'''


def render_html(m,prefix):
    e=lambda v:html.escape(str(v),quote=True)
    refs=lambda rows:refs_html(m,rows,prefix)
    badge=lambda status:f'<span class="badge {e(status)}">{e(status)}</span>'
    stats=m['metrics'];case=m['case']
    parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',f'<title>{e(m["title"])}</title><style>{CSS}</style><main>',
           f'<header><h1>{e(m["title"])}</h1><div>{e(m["trace"])}</div><p>{e(m["focus"]["question"])}</p><div>{e(m["focus"]["limitation"])}</div><p class="capture">Capture SHA-256: {e(m["capture_sha256"])}</p></header>',
           '<nav><a href="#milestones">既有規則</a><a href="#intents">寫入意圖</a><a href="#link">Link / DLLP</a><a href="#config">RC config</a><a href="#coverage">Coverage</a><a href="#sources">來源</a></nav><div class="stats">']
    for label,key in [('Packet observations','packet_observations'),('不同 packet anchors','distinct_packet_anchors'),('Config requests','config_requests'),('Observed read returns','observed_read_returns'),('Interval summaries','interval_summaries'),('HasErrors（window）','has_errors')]:parts.append(f'<div class="stat"><b>{stats[key]:,}</b>{label}</div>')
    parts += ['</div>',f'<div class="card"><h3>工程師回報{badge(case["reported_outcome"])}</h3><p>{e(case["reported_symptom"])}</p><p class="muted">Ground truth 來自工程師，不是 trace 自動判定。Crash dump verified: {e(case["crash_dump_verified"])}；其他測試的 {e(", ".join(case["other_tests_bsod"]))} 不當成本 capture 的 stop code。</p>{refs(m["case_evidence"])}<p>B1d COMPLETE · B2g SOURCE_SCOPE_GATE · B2h conditional · Root cause UNKNOWN</p></div>',
              '<section id="milestones"><h2>既有里程碑與產品規則</h2><p>雙向 valid training 支持 MUX connectivity；雙向有效 L0 是獨立觀察。缺觀察不改 FAIL，缺 threshold 不改 PASS。</p>']
    for r in m['rules']:
        parts.append(f'<details><summary>{e(r["title"])}{badge(r["status"])} <span class="muted">{e(r["id"])}</span></summary><p>{e(r["summary"])}</p><p class="muted">{e(r["limitation"])}</p><div class="source">{refs(r["evidence"])}</div></details>')
    parts += ['</section><section id="intents"><h2>LinkControl write intent</h2><p>Write＋Completion 不建立 applied state、System ASPM、產品違規或 BSOD 因果。</p>']
    for item in m['intents']:
        r=item['observation'];parts.append(f'<div class="card" id="packet-{r["packet_index"]}"><h3>Packet {r["packet_index"]} · {e(r["observation_kind"])}{badge(r["policy_result"])}</h3><p>{e(r["time_display"])} · {e(r["epoch"])} · {e(r["bdf"])} · Write intent {value(r["observed_write_intent"])} · ASPM intent {e(r["aspm_control_intent"])}</p><p>Effective: {e(r["effective_state"])} · Expected: {e(r["expected_state"])} · Policy: {e(r["policy_result"])}</p>{refs(item["evidence"])}</div>')
    parts += ['</section><section id="link"><h2>Link / DLLP 逐筆觀察</h2><div class="scroll"><table><tr><th>Packet</th><th>Display time</th><th>Direction</th><th>Observation</th><th>Evidence</th></tr>']
    for r in m['link']:parts.append(f'<tr id="link-{r["packet"]}-{e(r["kind"])}"><td>{r["packet"]}</td><td>{e(r["time"])}</td><td>{e(r["direction"])}</td><td>{e(link_description(r))}</td><td>{refs(r["evidence"])}</td></tr>')
    parts += ['</table></div></section><section id="config"><h2>RC config / Completion</h2><p>展開查看 request／Completion 關聯。讀回值附 Completion packet；Write DWORD 必須配合 BE，只代表意圖。</p>']
    for r in m['config']:
        ret=', '.join(f"{value(c['value'])} @ {c['packet']}" for c in r['returns_at_completion']) or 'UNKNOWN'
        parts.append(f'<details id="config-{r["packet"]}"><summary>Packet {r["packet"]} · {e(r["type"])} · {e(r["bdf"])} · offset {value(r["offset"])} <span class="muted">{e(r["time"])}</span></summary><p>Epoch: {e(r["epoch"])} · BE {value(r["first_be"])}/{value(r["last_be"])} · Write intent {value(r["write_intent"])}</p><p>Read return @ Completion: {e(ret)}</p><p>{e(r["value_status"])} · {e(r["association_outcome"])} · Cpl packets {e(r["completion_packets"])}</p><div class="source">{refs(r["evidence"])}</div></details>')
    parts += [f'</section><section id="coverage"><h2>Coverage、未觀察區間與 sample</h2><div class="card"><p>{stats["packet_observations"]} observations / {stats["distinct_packet_anchors"]} 不同 packet anchors 是抽取 coverage，不是 capture packet 總數。顯示時間小數位不是 timer accuracy，沒有建立更細的先後因果。</p>']
    parts += [f'<p>{e(x)}</p>' for x in m['coverage']]
    parts += [f'<p>雙向 L0 到尾端 display-time 差：{e(m["observations"]["post_l0_observed_seconds"])} sec；顯示時間無差不代表物理時間為零。 {refs(m["observation_evidence"])}</p>']
    for g in m['gaps']:parts.append(f'<p>{e(g["after_time"])}..{e(g["before_time"])}：{e(g["display_duration_seconds"])} sec display gap；packet {g["after_index"]} 與 {g["before_index"]} 之間無虛構 packet、不證明電氣靜默。 {refs(g["evidence"])}</p>')
    parts += [f'</div><details><summary>{len(m["intervals"])} 個 segment count summaries（非逐筆 TS／DLLP）</summary>']
    for r in m['intervals']:
        parts.append(f'<details><summary>Packet {r["first_index"]}..{r["last_index"]} · {r["counts"]["events"]:,} events · {r["counts"]["err_any"]:,} HasErrors</summary><p>{e(r["first_time"])}..{e(r["last_time"])} · Direction UNKNOWN</p><pre>{e(json.dumps(r["counts"],ensure_ascii=False,indent=2))}</pre>{refs(r["evidence"])}')
        for s in r['details']['gui_samples']:
            sample=s['sample'];parts.append(f'<p>GUI sample Packet {sample["packet_index"]} · {e(", ".join(sample["gui_error_labels"]))} · {e(sample["speed"])} GT/s {e(sample["width"])} · Time UNKNOWN（僅代表此 sample） {refs(s["evidence"])}</p>')
        parts.append('</details>')
    parts += ['</details><h2>後續需要的證據</h2><ul>']+[f'<li>{e(x)}</li>' for x in m['next_evidence']]
    parts += ['<li>OS 裝置可見性、driver/emulation logs 與 crash dump；目前 crash dump 未驗證。</li></ul><h2>Validation debt（不阻擋 B1d）</h2><ul>']
    parts += [f'<li>{e(d["id"])}{badge(d["status"])} · {e(d["reason"])}</li>' for d in m['validation_debt']]
    parts += ['</ul>'+refs(m['debt_evidence']),'<h2>限制</h2><ul>']+[f'<li>{e(x)}</li>' for x in m['limitations']]
    parts += ['</ul></section><section id="sources"><h2>Source registry</h2><p>來源 hash／pointer 可追溯；legacy link binding 是 corroborated，沒有冒充直接 capture hash。</p>']
    for key,s in m['sources'].items():parts.append(f'<details><summary>{e(key)} · {e(s["binding"])}</summary><p>{e(s["path"])}</p><pre>SHA-256 {e(s["sha256"])}</pre>{refs([contract.evidence(key,"")])}</details>')
    parts += ['</section><footer>離線 observation report · 無外部腳本／資源 · 尚未建立 root cause</footer></main></html>']
    return '\n'.join(parts)+'\n'


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('timeline','source-root','output-dir'):ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        contract.require(not args.output_dir.exists(),'Refusing existing output')
        doc=adapter.verified_timeline(args.timeline,args.source_root)
        model=build_model(doc,args.source_root)
        prefix=Path(os.path.relpath(args.source_root,args.output_dir)).as_posix()
        markdown=render_markdown(model,prefix); webpage=render_html(model,prefix)
        args.output_dir.mkdir(parents=True)
        (args.output_dir/'report.md').write_text(markdown,encoding='utf-8',newline='\n')
        (args.output_dir/'report.html').write_text(webpage,encoding='utf-8',newline='\n')
        print(json.dumps({'status':'PASS_OBSERVATION_REPORT','rules':len(model['rules']),'config_requests':len(model['config'])}))
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError,AttributeError) as exc:
        print(str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
