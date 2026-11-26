"""Streaming G1/G2 validation and disk-backed G2/G3 analysis, preserving G9 rules."""
import json
from pathlib import Path
import html
import csv

import pcie_event_coverage as nav
import pcie_disk_index as disk
import pcie_large_io as large


class Messages:
    def __init__(self,fields):self.fields=fields
    def __len__(self):return self.fields.db.execute('SELECT count(*) FROM messages').fetchone()[0]
    def __iter__(self):
        for (data,) in self.fields.db.execute('SELECT data FROM messages ORDER BY ordinal'):yield json.loads(data)
    def unattached(self,attached):
        return (dict(packet=m['packet_index'],display_time=m['time_display'],message_name=m['message_code_name'],routing=m['message_route_name'],requester_id=m['requester_id']) for m in self if m['packet_index'] not in attached)


def save(path,value):
    large.write_json_bounded(path,value)


def tsv(path,rows,columns,root):
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,delimiter='\t',lineterminator='\n');writer.writeheader()
        for n,row in enumerate(rows):
            if n%512==0:
                if (root/'cancel.json').exists():raise InterruptedError('Cancelled during TSV export')
                large.check_disk(root)
            writer.writerow({k:'NA' if row[k] is None else row[k] for k in columns})


def validate_inputs(manifest,root):
    root=Path(root);storage=manifest['storage'];path=root/'transactions.sqlite'
    if storage.get('schema')!=disk.FORMAT or storage['sha256']!=nav.digest(path):raise ValueError('Disk index identity mismatch')
    seal=json.loads((root/'disk-index.json').read_text(encoding='utf-8'))
    if seal['display_sha256']!=manifest['trace']['sha256'] or seal['total']!=manifest['trace']['tlp_count']:raise ValueError('Disk index trace binding mismatch')
    if seal['sha256']!=storage['sha256'] or seal['status']!='SEALED':raise ValueError('Unsealed disk index')
    for name in ('rows','fields','messages','count'):
        if nav.digest(root/(name+'.txt'))!=seal['raw_sha256'][name]:raise ValueError('Raw evidence changed after index verification')
    for name in ('fields','messages'):
        p=Path(manifest[name]['path']).resolve()
        if not p.is_relative_to(root.resolve()) or nav.digest(p)!=manifest[name]['sha256']:raise ValueError('Canonical export mismatch')
    fields=disk.Fields(path)
    try:
        if len(fields)!=seal['total'] or fields.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid disk index')
    finally:fields.close()


def finish(root,trace_info,total,batch_size=4096,diagnostic_exports='full'):
    if diagnostic_exports not in ('full','on_demand'):raise ValueError('Unknown diagnostic export mode')
    import g2b_associate as g2
    import verify_g1b_rows as g1_rows
    import verify_g2a_fields as g2_fields
    import g3_candidates as g3
    import g3c_nearby_messages as g3c
    import g3d_context as g3d
    import g3e_groups as g3e
    import g3f_findings as g3f
    root=Path(root)
    index=disk.ingest(root,total,batch_size)
    index.chmod(0o444)
    source_sha=trace_info['source_trace']['sha256'];display_sha=trace_info['display_trace']['sha256']
    seal=dict(schema=disk.FORMAT,status='SEALED',sha256=nav.digest(index),source_sha256=source_sha,
        display_sha256=display_sha,total=total,batch_rows=batch_size,sqlite_cache_bytes=8*1024*1024,
        raw_sha256={name:nav.digest(root/(name+'.txt')) for name in ('count','rows','fields','messages')},
        association='Unchanged G2b nearest preceding RequesterId/Tag; no chunk-end timeout or completion inference')
    save(root/'disk-index.json',seal)
    fields=disk.Fields(index);requests=disk.Requests(fields);messages=Messages(fields)
    cancelled=lambda:(root/'cancel.json').exists()
    try:
        # Complete canonical evidence exports remain readable by the legacy CLI.
        for name in ('rows','fields','messages'):(root/('verified-'+name)).mkdir()
        fields_sha=disk.write_array(root/'verified-fields/fields.json',fields,cancelled)
        msg_sha=disk.write_array(root/'verified-messages/messages.json',messages,cancelled)
        save(root/'verified-fields/summary.json',dict(status='PASS_FIELD_PROBE_OUTPUT',rows=total,log_sha256=nav.digest(root/'fields.txt'),fields_json_canonical_sha256=fields_sha,storage=disk.FORMAT))
        save(root/'verified-messages/summary.json',dict(status='PASS_MESSAGE_FIELD_PROBE_OUTPUT',rows=len(messages),messages_json_sha256=msg_sha,g2a_fields_sha256=fields_sha,storage=disk.FORMAT))
        manifest=dict(schema_version='pcie.triage-input/v1',trace=dict(file_name='display-working.pex',sha256=display_sha,tlp_count=total),
            fields=dict(path=str(root/'verified-fields/fields.json'),sha256=fields_sha,verifier_summary=str(root/'verified-fields/summary.json')),
            messages=dict(path=str(root/'verified-messages/messages.json'),sha256=msg_sha,verifier_summary=str(root/'verified-messages/summary.json')),
            storage=dict(schema=disk.FORMAT,path=str(index),sha256=seal['sha256']))
        save(root/'triage-input.json',manifest)
        report=root/'report';report.mkdir();stage=report/'stages';stage.mkdir()
        if diagnostic_exports=='full':
            import pcie_dense_exports
            pcie_dense_exports.export(root,fields,requests)
        # The bounded evidence graph is separate from the unbounded row/index store.
        graph_rows=fields.db.execute('SELECT count(*) FROM requests WHERE next_request IS NOT NULL').fetchone()[0]
        graph_rows+=fields.db.execute('SELECT count(*) FROM completions c JOIN fields f ON f.packet=c.packet WHERE c.request IS NOT NULL AND json_extract(f.data,\'$.compl_status\')!=0').fetchone()[0]
        if graph_rows>disk.GRAPH_ROWS:raise large.ResourceLimit('TLP rows indexed completely; candidate evidence graph exceeds current bounded graph budget. Full associations retained on disk; no completed diagnosis published.')
        candidates=g3.detect(requests)
        # Existing algorithms use indexed packet/ordinal access; all source rows remain present.
        nearby,unattached=g3c.attach(candidates,fields,messages) if candidates else ([],messages.unattached(set()))
        disk.write_array(stage/'unattached_messages.json',unattached,cancelled)
        nearby_doc=dict(candidates=nearby)
        contexts=dict(candidates=g3d.build(fields,None,requests,candidates,nearby_doc))
        groups=dict(groups=g3e.group(candidates,requests,nearby_doc),detectors=g3.DETECTORS)
        findings=g3f.build(groups,candidates,nearby_doc,contexts,fields)
        named=dict(candidates=dict(candidates=candidates,detectors=g3.DETECTORS),nearby=nearby_doc,contexts=contexts,groups=groups)
        for name,value in named.items():save(stage/(name+'.json'),value)
        inputs={name:dict(path=str(stage/(name+'.json')),sha256=nav.digest(stage/(name+'.json'))) for name in named}
        inputs.update(fields=manifest['fields'],messages=manifest['messages'])
        # Keep the G3f presentation contract; storage and runner provenance are explicit.
        document=dict(schema_version=g3f.SCHEMA_VERSION,inputs=inputs,trace_ground_truth='UNKNOWN',
            ordering='capture order of primary Go to Packet; not a ranking',
            segmentation='G3d context blocks merged when their TLP row ranges overlap; display only, membership unchanged',
            findings_total=len(findings),findings=findings)
        save(report/'findings.json',document)
        (report/'report.md').write_text('# PCIe disk-backed evidence\n\nComplete rows and associations: transactions.sqlite. Auxiliary JSON/TSV: '+diagnostic_exports+'.\nFull workspace report is in the parent job folder.\n',encoding='utf-8')
        (report/'report.html').write_text('<!doctype html><meta charset="utf-8"><p>Complete indexed evidence: transactions.sqlite. Open the workspace report in the parent job folder.</p>',encoding='utf-8')
        save(report/'run-manifest.json',dict(schema_version='pcie.triage-run-manifest/v1',runner='pcie_dense_analysis',
            storage=disk.FORMAT,status='PASS',input_manifest=dict(path=str(root/'triage-input.json'),sha256=nav.digest(root/'triage-input.json')),
            package={name:nav.digest(report/name) for name in ('findings.json','report.md','report.html')},findings_total=len(findings)))
        locators=[]
        for f in findings:
            row=fields.packet_map[f['where_to_look']['primary_go_to_packet']]
            locators.append(dict(finding_id=f['finding_id'],source_trace_sha256=source_sha,display_trace_sha256=display_sha,
                packet_namespace='converted_trace_packet_zero_based' if source_sha!=display_sha else 'native_trace_packet_zero_based',display_level=0,
                packet_index=row['packet_index'],timestamp=None,time_display=row['time_display'],time_precision='vendor_display_text_only',
                channel=row['channel'],direction=row['channel'] if row['channel'] in ('Upstream','Downstream') else 'UNKNOWN'))
        result=dict(status='ANALYSIS_COMPLETE',findings_total=len(findings),locators=locators,ordering=document['ordering'],
            coverage='Existing TLP association/message analysis only; no full PCIe compliance verdict.',product_verdict='NOT_EVALUATED',
            native_navigation='MANUAL_CTRL_G',working_copy=str(root/'display-working.pex'),storage=disk.FORMAT,
            diagnostic_exports=diagnostic_exports)
        save(root/'analysis.json',result)
        validate_inputs(manifest,root)
        return result
    finally:fields.close()
