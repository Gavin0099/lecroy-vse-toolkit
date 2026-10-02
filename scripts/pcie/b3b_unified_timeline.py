#!/usr/bin/env python3
"""W2+W3: replay existing config/TLP and bounded link observations together."""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path, PureWindowsPath
import sys
import b1c_training_timeline as b1c
import b1d_mux_rules as b1d
import b1e_link_findings as b1e
import b2a_register_fields as b2a
import b2b_config_access as b2b
import b2g_watchlist_prepare as b2g
import b3a_event_contract as contract
import g2b_associate as g2b

JSON_INPUTS = {'metadata','probe','raw_probe','raw_run','accesses','evaluation','context','training',
               'reference','watchlist','link_timeline','link_summary','haserrors',
               'haserrors_summary','gui','findings'}
TEXT_INPUTS = {'raw_text','engineer_source'}
require = contract.require


def inputs(root, manifest_path):
    root = Path(root).resolve(); manifest_path = Path(manifest_path).resolve()
    require(manifest_path.is_relative_to(root), 'Manifest outside source root')
    manifest_raw = manifest_path.read_bytes(); manifest = json.loads(manifest_raw)
    require(isinstance(manifest, dict) and set(manifest) == JSON_INPUTS | TEXT_INPUTS, 'Unsupported manifest inputs')
    raw = {}; paths = {}
    for key, name in manifest.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root), 'Input outside source root')
        raw[key] = path.read_bytes(); paths[key] = path.relative_to(root).as_posix()
    raw['manifest'] = manifest_raw; paths['manifest'] = manifest_path.relative_to(root).as_posix()
    return raw, paths


def verify_config(raw, data):
    """Verify byte lineage and replay old log without changing historical bytes."""
    probe, fresh, meta, run = (data[k] for k in ('probe','raw_probe','metadata','raw_run'))
    capture = probe['input']['trace']
    require(capture == fresh['input']['trace'] == run['pre']['files'][0], 'Different config capture')
    for doc in (probe,fresh):
        require(doc['input']['metadata_sha256'] == contract.sha(raw['metadata']), 'Changed metadata source')
    require(fresh['input']['com_run_sha256'] == contract.sha(raw['raw_run']) and
            fresh['input']['vse_output_sha256'] == contract.sha(raw['raw_text']) == run['output']['vse_output_sha256'],
            'Raw probe receipt/output identity mismatch')
    require(run['status'] == 'COM_RUN_COMPLETE' and run['identities_unchanged'] and
            run['steps']['finish_event']['result_name'] == 'DONE', 'Unqualified raw run')
    rows, end = b2a.parse(raw['raw_text'].decode('utf-8'))
    counts = b2a.verify(rows, end, meta, require_full_payload=True)
    require(fresh['schema'] == b2a.SCHEMA and fresh['status'] == 'PASS_REGISTER_FIELD_PROBE'
            and rows == fresh['rows'] and counts == fresh['counts'] and end['tlps'] == fresh['tlps'],
            'Fresh raw proof differs from replay')
    require(len(probe['rows']) == len(rows), 'Legacy/fresh probe coverage differs')
    for old, new in zip(probe['rows'], rows):
        require({k:v for k,v in old.items() if k != 'frame_prefix'} ==
                {k:v for k,v in new.items() if k != 'frame_prefix'} and new['frame_prefix'].startswith(old['frame_prefix']),
                'Legacy fields differ from full raw proof')
    evaluation, training, log = (data[k] for k in ('evaluation','training','accesses'))
    for target, key in [('training','training_sha256'),('engineer_source','source_document_sha256')]:
        require(evaluation['input'][key] == contract.sha(raw[target]), 'Changed engineer/training source')
    context = evaluation['product_context']
    require(context == data['context'] and evaluation['input']['context_sha256'] == contract.sha(raw['context']),
            'Changed product context source')
    require(PureWindowsPath(capture['path']).name == context['case']['trace_basename'], 'Different engineer trace basename')
    require(context['training_sha256'] == contract.sha(raw['training']) and
            context['provenance']['document_sha256'] == contract.sha(raw['engineer_source']), 'Context identity differs')
    require(b1d.evaluate(training, context) == {k:v for k,v in evaluation.items() if k != 'input'}, 'B1d replay differs')
    for key, target in [('probe_sha256','probe'),('metadata_sha256','metadata'),
                        ('b1d_evaluation_sha256','evaluation'),('training_sha256','training')]:
        require(log['input'][key] == contract.sha(raw[target]), 'Config log input identity mismatch')
    op = context['operation']
    require(b2b.build(probe,meta,op['disconnect_packet'],op['reconnect_packet']) ==
            {k:v for k,v in log.items() if k != 'input'}, 'Config log differs from reconstruction')
    watch = data['watchlist']
    for key, target in [('log_sha256','accesses'),('reference_sha256','reference'),('evaluation_sha256','evaluation')]:
        require(watch['input'][key] == contract.sha(raw[target]), 'Watchlist input differs')
    require(b2g.build(log,data['reference'],evaluation) == {k:v for k,v in watch.items() if k != 'input'},
            'Watchlist observations differ from replay')
    return capture['sha256'], counts


def config_events(doc, data):
    meta, probe, log = (data[k] for k in ('metadata','probe','accesses'))
    fields = {r['packet_index']:(i,r) for i,r in enumerate(probe['rows'])}
    requests = {r['packet_index']:(i,r) for i,r in enumerate(log['accesses'])}
    replies = {}
    for i, request in enumerate(log['accesses']):
        for j, completion in enumerate(request['completions']):
            replies.setdefault(completion['packet_index'],[]).append((i,j,request))
    orphan = {r['packet_index']:i for i,r in enumerate(log['unmatched_completion_candidates'])}
    watch = {r['packet_index']:(i,r) for i,r in enumerate(data['watchlist']['observations'])}
    for i, row in enumerate(meta):
        packet = row['packet_index']; role = g2b.classify(row)
        refs = [contract.evidence('metadata',f'/{i}')]
        details = {'metadata':row, 'vendor_type_name':role['vendor_type_name'], 'role':role['role'],
                   'config_request':None, 'config_completions':[], 'unmatched_completion_candidate':packet in orphan,
                   'register_write_intent':None}
        bdf = None; classification = 'OBSERVATION'
        if packet in fields:
            index, field = fields[packet]
            refs += [contract.evidence('probe',f'/rows/{index}'),contract.evidence('raw_probe',f'/rows/{index}')]
            details['probe_fields'] = field
        if packet in requests:
            index, request = requests[packet]; refs.append(contract.evidence('accesses',f'/accesses/{index}'))
            # Returned values are represented at Completion below, never at request time.
            details['config_request'] = {k:v for k,v in request.items() if k not in {'read_value','completions','evidence'}}
            details['config_request']['completion_packets'] = [c['packet_index'] for c in request['completions']]
            bdf = request['target_bdf']
            if request['write_value'] is not None: classification = 'WRITE_INTENT'
        for index, j, request in replies.get(packet,[]):
            refs.append(contract.evidence('accesses',f'/accesses/{index}/completions/{j}'))
            same_epoch = contract.epoch_at(doc['anchors'],packet) == request['epoch']
            details['config_completions'].append({'access_id':request['access_id'], 'request_packet':request['packet_index'],
                'request_epoch':request['epoch'], 'same_epoch':same_epoch, 'value_status':request['value_status'],
                'read_return_observation':request['read_value'] if same_epoch else None,
                'association_outcome':request['association_outcome'], 'target_bdf':request['target_bdf']})
        if packet in orphan: refs.append(contract.evidence('accesses',f"/unmatched_completion_candidates/{orphan[packet]}"))
        if packet in watch:
            index, intent = watch[packet]; refs.append(contract.evidence('watchlist',f'/observations/{index}'))
            details['register_write_intent'] = intent
        doc['events'].append(contract.packet_event(packet,row['time_display'],'TLP','TLP',row['channel'] or 'UNKNOWN',
                                                   doc['anchors'],refs,details,bdf,classification))


def verify_link(raw, data, capture):
    summary, training, gui = (data[k] for k in ('link_summary','training','gui'))
    require(summary['status'] == 'PASS_WINDOW_EXPORT' and summary['named_with_constants'] and
            summary['timeline_json_sha256'] == contract.sha(raw['link_timeline']), 'Unqualified link timeline')
    require(gui['trace_sha256'] == capture, 'Different GUI capture')
    for key, target in [('timeline_sha256','link_timeline'),('x2_sha256','haserrors'),('gui_sha256','gui')]:
        require(training['input'][key] == contract.sha(raw[target]), 'Changed training input')
    require(training['input']['window'] == summary['window'], 'Different link window')
    require(data['haserrors_summary']['status'] == 'PASS_HASERRORS_PROBE_OUTPUT' and
            data['haserrors_summary']['b1b_totals_crosscheck'] == 'MATCHED', 'Unqualified HasErrors summary')
    require(data['haserrors_summary']['end']['events'] == summary['totals']['events'] and
            data['haserrors_summary']['end']['has_errors'] == summary['totals']['err_any'], 'HasErrors summary totals differ')
    require(data['haserrors_summary']['end'] == data['haserrors']['end'], 'HasErrors summary differs from source end')
    head = data['haserrors']['header']
    require((head['start'],head['end']) == (summary['window']['start'],summary['window']['end']), 'Different HasErrors window')
    require(b1c.build(data['link_timeline'],Decimal(training['parameters']['gap_seconds']),data['haserrors'],gui)
            == training['phases'], 'Training phases differ from replay')
    counts = Counter(r['kind'] for r in data['link_timeline'])
    require({k:v for k,v in counts.items() if k != 'segment'} == summary['records_by_kind'], 'Link record coverage differs')
    segments = [r for r in data['link_timeline'] if r['kind'] == 'segment']
    require(len(segments) == summary['totals']['segments'] and sum(r['events'] for r in segments) == summary['totals']['events']
            and sum(r['tlp'] for r in segments) == summary['totals']['tlp']
            and sum(r['err_any'] for r in segments) == summary['totals']['err_any'], 'Link segment totals differ')
    meta = {r['packet_index']:r for r in data['metadata']}
    for row in data['link_timeline']:
        if row['kind'] == 'tlp':
            m = meta.get(row['packet_index'])
            require(m is not None and (m['channel'],m['time_display'],int(m['tlp_type_hex'],16)) ==
                    (row['channel'],row['time_display'],row['tlp_type']), 'Link/TLP overlap differs')
    findings = data['findings']
    for key,target in [('evaluation_sha256','evaluation'),('training_sha256','training'),('source_document_sha256','engineer_source')]:
        require(findings['input'][key] == contract.sha(raw[target]), 'Findings input differs')
    require(b1e.build(data['evaluation'],training) == {k:v for k,v in findings.items() if k != 'input'}, 'B1e findings differ from replay')


def link_events(doc, data):
    events = {r['event_id']:r for r in doc['events']}
    timeline = data['link_timeline']; gui = data['gui']
    layer = {'link_condition':'LINK','ltssm':'TRAINING','speed_width':'LINK','nak':'DLLP'}
    for i,row in enumerate(timeline):
        refs = [contract.evidence('link_timeline',f'/{i}')]
        if row['kind'] == 'segment':
            counts = {k:v for k,v in row.items() if type(v) is int and k not in {'packet_index','seg','first_index','last_index'}}
            samples = [{'sample':r,'evidence':[contract.evidence('gui',f'/ts1_error_samples/{j}')]} for j,r in enumerate(gui['ts1_error_samples'])
                       if row['first_index'] <= r['packet_index'] <= row['last_index']]
            doc['intervals'].append({'kind':'SEGMENT_COUNTS','first_index':row['first_index'],'last_index':row['last_index'],
                'first_time':row['first_time'],'last_time':row['last_time'],
                'first_display_quantum_seconds':contract.time_parts(row['first_time'])[1],
                'last_display_quantum_seconds':contract.time_parts(row['last_time'])[1], 'direction':'UNKNOWN',
                'counts':counts,'details':{'gui_samples':samples,'sample_only':True,
                                        'sample_times':'UNKNOWN; no timestamp synthesized from interval endpoints'},'evidence':refs})
        elif row['kind'] == 'tlp':
            event = events[f"packet:{row['packet_index']}:TLP:TLP"]
            event['evidence'].extend(refs); event['details']['link_window_record'] = row
        else:
            require(row['kind'] in layer, 'Unsupported link observation kind')
            doc['events'].append(contract.packet_event(row['packet_index'],row['time_display'],layer[row['kind']],row['kind'],
                row.get('channel') or 'UNKNOWN',doc['anchors'],refs,{'link_record':row}))
    for i,phase in enumerate(data['training']['phases']):
        if phase['kind'] == 'NO_OBSERVED_EVENTS':
            doc['gaps'].append({k:phase[k] for k in ['after_index','before_index','after_time','before_time']} |
                {'after_display_quantum_seconds':contract.time_parts(phase['after_time'])[1],
                 'before_display_quantum_seconds':contract.time_parts(phase['before_time'])[1],
                 'display_duration_seconds':phase['duration_seconds'],'claim':'NO_OBSERVED_EVENTS_IN_SOURCE_WINDOW',
                 'evidence':[contract.evidence('training',f'/phases/{i}'),contract.evidence('link_timeline','')]})
    for i,rule in enumerate(data['evaluation']['evaluations']):
        doc['milestones'].append({'id':rule['rule_id'],'status':rule['status'],
            'basis':'B1D_OBSERVATION_MILESTONE' if rule['rule_id']=='BIDIRECTIONAL_L0' or rule.get('assessment_kind')=='observation_only' else 'B1D_EXISTING_RULE',
            'summary':rule['summary'],'evidence':[contract.evidence('evaluation',f'/evaluations/{i}')]})
    doc['events'].sort(key=lambda r:(r['packet_index'],r['event_id']))


def build(root, manifest_path):
    raw, paths = inputs(root,manifest_path)
    data = {k:json.loads(raw[k]) for k in JSON_INPUTS}
    capture, counts = verify_config(raw,data)
    verify_link(raw,data,capture)
    doc = contract.new_document(capture,data['accesses']['anchors'])
    for name in sorted(JSON_INPUTS | {'manifest'}):
        binding = ('CAPTURE_DECLARED' if name in {'probe','raw_probe','raw_run','gui'} else
                   'CORROBORATED_LEGACY' if name in {'training','link_timeline','link_summary','haserrors','haserrors_summary','evaluation','context','findings'} else 'DERIVED_VIA_PROBE')
        doc['sources'][name] = contract.source_record(paths[name],raw[name],capture,binding)
    config_events(doc,data); link_events(doc,data)
    doc['coverage'] = [f"G2a TLP callback records: {len(data['metadata'])}; not a full per-packet non-TLP export.",
        f"Link window: {data['link_summary']['window']['start']}..{data['link_summary']['window']['end']}; {sum(data['link_summary']['records_by_kind'].values())} explicit link/DLLP/TLP records plus {len(doc['intervals'])} segment count summaries.",
        f"GUI TS error evidence: {len(data['gui']['ts1_error_samples'])} samples only; no per-sample timestamps or population subtype distribution."]
    doc['limitations'] = ['Legacy B1 link files have no direct capture hash; binding is corroborated by GUI declared capture, source lineage and four matching TLP overlaps.',
        'Read returns become observations at Completion; cross-epoch returns cannot supply old-device state. Writes remain intent, Completion is not applied-state proof.',
        'Invalid LTSSM markers preserved; NAK does not establish replay; segment counts are not individual DLLP/TS packets.',
        'Post-L0 capture tail is short; missing config/speed observations cannot establish absence, policy violation or BSOD root cause.']
    doc['extensions'] = {'producer':{'adapter':'b3b_unified_timeline','manifest_path':paths['manifest'],'manifest_sha256':contract.sha(raw['manifest'])},
        'input_validation':{'full_raw_probe_counts':counts,'config_summary':data['accesses']['summary'],
                            'link_summary':data['link_summary']['totals'],'raw_text_sha256':contract.sha(raw['raw_text']),
                            'engineer_source_sha256':contract.sha(raw['engineer_source'])}}
    contract.validate(doc,{k:raw[k] for k in JSON_INPUTS | {'manifest'}})
    return doc


def verified_timeline(path, root):
    """Consumers verify canonical bytes by recomputing the adapter, not trusting prose."""
    raw = Path(path).read_bytes(); doc = json.loads(raw)
    producer = doc['extensions']['producer']
    require(producer['adapter'] == 'b3b_unified_timeline', 'Unsupported timeline producer')
    root = Path(root).resolve(); manifest = (root / producer['manifest_path']).resolve()
    require(manifest.is_relative_to(root) and contract.sha(manifest.read_bytes()) == producer['manifest_sha256'], 'Changed/outside manifest')
    require(raw == canonical_bytes(build(root,manifest)), 'Timeline bytes differ from canonical source-bound adapter replay')
    return doc


def canonical_bytes(doc):
    return (json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','source-root','output-dir'): ap.add_argument('--'+name,type=Path,required=True)
    args = ap.parse_args(argv)
    try:
        require(not args.output_dir.exists(), 'Refusing existing output')
        doc = build(args.source_root,args.manifest)
        args.output_dir.mkdir(parents=True)
        (args.output_dir/'timeline.json').write_bytes(canonical_bytes(doc))
        print(json.dumps({'status':'PASS_UNIFIED_OBSERVATION_TIMELINE','observations':len(doc['events']),
                          'distinct_observed_packets':len({r['packet_index'] for r in doc['events']}),
                          'intervals':len(doc['intervals']),'gaps':len(doc['gaps'])}))
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError,AttributeError) as exc:
        print(str(exc),file=sys.stderr); return 2
    return 0


if __name__ == '__main__': raise SystemExit(main())
