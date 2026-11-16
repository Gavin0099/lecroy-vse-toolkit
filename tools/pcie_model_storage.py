"""Seal bounded native evidence arrays separately from the desktop summary.

These arrays are already capped by the native phase/transaction subscriptions;
unbounded TLP rows live in SQLite, never in this desktop model.
"""
import json
from pathlib import Path
import uuid
import pcie_large_io as large
import pcie_event_coverage as nav

FORMAT='pcie.external-model/v1'
MAX_BYTES=64*1024*1024
PATHS=(('flow_transaction_evidence',),('transaction_crosscheck',),('flow_analysis','transaction_checks'),
       ('stage_summary','events'),('stage_summary','observed_milestones'))


def parent(model,path):
    value=model
    for key in path[:-1]:
        if key not in value or not isinstance(value[key],dict):return None
        value=value[key]
    return value


def pack(model,root):
    if model.get('external_model'):return model
    result=dict(model)
    for key in ('flow_analysis','stage_summary'):
        if isinstance(model.get(key),dict):result[key]=dict(model[key])
    refs=[];root=Path(root);generation='model-evidence-'+uuid.uuid4().hex;folder=root/generation;folder.mkdir()
    for path in PATHS:
        node=parent(result,path)
        if node is None or node.get(path[-1]) is None:continue
        value=node[path[-1]];file=folder/('-'.join(path)+'.json')
        large.write_json_bounded(file,value,MAX_BYTES);file.chmod(0o444)
        ref=dict(keys=list(path),path=str(file),sha256=nav.digest(file),bytes=file.stat().st_size,
            source_trace_sha256=model['source_trace_sha256'],display_trace_sha256=model['display_trace_sha256'],analysis_id=model['analysis_id'])
        refs.append(ref)
        if isinstance(value,list):node[path[-1]]=[]
        else:
            node[path[-1]]={k:v for k,v in value.items() if not isinstance(v,(list,dict))}
            node[path[-1]].update(external_evidence=ref,retained_array_counts={k:len(v) for k,v in value.items() if isinstance(v,list)})
    result['external_model']=dict(schema=FORMAT,refs=refs,meaning='Desktop projection; arrays are external, not absent. Full source evidence retained.')
    notice='大量原生交易與階段證據分檔保存；桌面摘要不攜帶完整陣列，請展開工作資料夾中的證據附件。'
    result['limitations']=list(model['limitations'])+([] if notice in model['limitations'] else [notice])
    return result


def expand(model):
    meta=model.get('external_model')
    if meta is None:return model
    if meta.get('schema')!=FORMAT:raise ValueError('Unknown external model contract')
    root=Path(model['display_trace_path']).resolve().parent
    result=dict(model)
    for key in ('flow_analysis','stage_summary'):
        if isinstance(model.get(key),dict):result[key]=dict(model[key])
    seen=set()
    for ref in meta['refs']:
        path=tuple(ref['keys']);file=Path(ref['path']).resolve(strict=True)
        if path not in PATHS or path in seen or not file.is_relative_to(root):raise ValueError('Invalid external evidence path')
        seen.add(path)
        if any(ref[k]!=model[k] for k in ('source_trace_sha256','display_trace_sha256','analysis_id')):raise ValueError('External evidence belongs to another trace/job')
        large.check_file(file,MAX_BYTES)
        if file.stat().st_size!=ref['bytes'] or nav.digest(file)!=ref['sha256']:raise ValueError('External evidence content changed')
        node=parent(result,path)
        if node is None:raise ValueError('Missing external evidence parent')
        node[path[-1]]=json.loads(file.read_text(encoding='utf-8'))
    result.pop('external_model')
    return result
