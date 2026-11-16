"""Bounded desktop projection; full inspection/evidence stays in the job folder."""
import json
import os
from pathlib import Path
import uuid
import pcie_large_io as large

MAX_BYTES=1024*1024
PAGE_ROWS=20


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')


def write(root,model,publish=True):
    root=Path(root)
    generation='ui-'+uuid.uuid4().hex
    dest=root/generation;dest.mkdir()
    base={k:v for k,v in model.items() if k not in
          ('candidates','observations','flow_items','flow_analysis','stage_summary','flow_transaction_evidence',
           'transaction_crosscheck','native_details')}
    flow=model.get('flow_analysis',{})
    base['flow_analysis']={k:v for k,v in flow.items() if k not in
                          ('scenarios','completion_observations','transaction_checks','knowledge_only','packet_findings','priority_order')}
    # Explicit disclosure: the complete chain is in the original report, not this projection.
    stage=model.get('stage_summary')
    if stage:
        base['stage_summary']={k:v for k,v in stage.items() if k not in ('observed_milestones','recommended_checks','events')}
        base['stage_summary']['observed_milestones']=[]
        base['stage_summary']['coverage_and_limitations']=list(stage.get('coverage_and_limitations',[]))+[
            '此頁只載入目前項目的證據；完整階段鏈保留在 flow-analysis.json 與 analysis/stage-summary.json。']
    scenarios={e['scenario_id']:e for e in flow.get('scenarios',[])}
    displayed=flow.get('displayed_scenarios',[])
    groups={}
    for name in ('flow_items','candidates','observations'):
        rows=model.get(name,[])
        if name=='flow_items':
            by_id={r.get('scenario_id'):r for r in rows}
            rows=[by_id[sid] for sid in displayed if sid in by_id]+[r for r in rows if r.get('scenario_id') not in displayed]
        count=len(rows);pages=[];chunk=[]
        def page(items,index):
            value=dict(base,candidates=[],observations=[],flow_items=[])
            value[name]=items
            if name=='candidates':
                value['observations']=model.get('observations',[])[:1]
            value['flow_analysis']=dict(base['flow_analysis'],scenarios=[
                scenarios[r['scenario_id']] for r in items if r.get('scenario_id') in scenarios])
            value['ui_page']=dict(group=name,page=index,total=count,
                flow_total=len(model.get('flow_items',[])),candidate_total=len(model.get('candidates',[])),
                full_evidence='inspection.json')
            return value
        def flush():
            data=encoded(page(chunk,len(pages)))
            if len(data)>MAX_BYTES:raise ValueError('單一 UI 項目超過有界頁面上限；完整證據保留，未載入畫面。')
            filename=name+'-'+str(len(pages))+'.json'
            large.check_disk(dest,len(data))
            (dest/filename).write_bytes(data);pages.append(generation+'/'+filename)
        for row in rows:
            if chunk and (len(chunk)>=PAGE_ROWS or len(encoded(page(chunk+[row],len(pages))))>MAX_BYTES):
                flush();chunk=[]
            chunk.append(row)
        flush()
        groups[name]=dict(total=count,pages=pages)
    index=dict(schema='pcie.desktop-pages/v1',analysis_id=model['analysis_id'],groups=groups)
    if publish:publish_index(root,index)
    return index


def publish_index(root,index):
    root=Path(root)
    temporary=root/'ui-index.json.tmp';temporary.write_bytes(encoded(index))
    os.replace(temporary,root/'ui-index.json')
