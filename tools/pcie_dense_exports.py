"""Optional diagnostic copies of the complete, sealed PCIe disk index.

Desktop analysis needs canonical fields/messages and the complete index, not
duplicate row/role/association JSON and TSV. CLI defaults retain full exports.
Run --root ANALYSIS [--output NEW_FOLDER] after a desktop run to create them.
Never opens or changes a .pex file; existing evidence is never overwritten.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/pcie'))

import pcie_disk_index as disk
import pcie_large_io as large
import pcie_event_coverage as nav


def tsv(path, rows, columns, root):
    partial=path.with_name(path.name+'.partial')
    with partial.open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,delimiter='\t',lineterminator='\n')
        writer.writeheader()
        for n,row in enumerate(rows):
            if n%512==0:
                if (root/'cancel.json').exists():raise InterruptedError('Cancelled during TSV export')
                large.check_disk(path.parent)
                large.check_file(partial,large.DEFAULTS['dense_probe_bytes'])
            writer.writerow({k:'NA' if row[k] is None else row[k] for k in columns})
        stream.flush();os.fsync(stream.fileno())
    large.check_file(partial,large.DEFAULTS['dense_probe_bytes'])
    if path.exists():raise FileExistsError(path)
    partial.rename(path)


def export(root, fields, requests, output=None):
    import g2b_associate as g2
    import verify_g1b_rows as g1_rows
    import verify_g2a_fields as g2_fields
    root=Path(root);dest=root if output is None else Path(output).resolve()
    if (root/'cancel.json').exists():raise InterruptedError('Cancelled before diagnostic export')
    seal=json.loads((root/'disk-index.json').read_text(encoding='utf-8'))
    before=nav.digest(fields.path)
    if fields.path.resolve()!=(root/'transactions.sqlite').resolve() or before!=seal['sha256']:raise ValueError('Diagnostic source index mismatch')
    if output is not None:dest.mkdir(parents=True,exist_ok=False)
    if (dest/'diagnostic-exports.json').exists():raise FileExistsError(dest/'diagnostic-exports.json')
    names=('verified-rows/rows.json','verified-rows/rows.tsv','verified-fields/fields.tsv',
           'report/stages/associations.json','report/stages/roles.json','report/stages/orphan_completions.json')
    for name in names:
        p=dest/name
        if not p.resolve().is_relative_to(dest.resolve()):raise ValueError('Diagnostic destination escapes output folder')
        if p.exists() or p.is_symlink() or p.with_name(p.name+'.partial').exists():raise FileExistsError(p)
    for name in names:(dest/name).parent.mkdir(parents=True,exist_ok=True)
    cancelled=lambda:(root/'cancel.json').exists()
    rows=lambda:(json.loads(r[0]) for r in fields.db.execute('SELECT data FROM rows ORDER BY ordinal'))
    disk.write_array(dest/names[0],rows(),cancelled)
    tsv(dest/names[1],rows(),g1_rows.COLUMNS,root)
    tsv(dest/names[2],fields,g2_fields.COLUMNS,root)
    disk.write_array(dest/names[3],requests,cancelled)
    disk.write_array(dest/names[4],(g2.classify(f) for f in fields),cancelled)
    disk.write_array(dest/names[5],(requests.completion(p[0]) for p in fields.db.execute('SELECT packet FROM completions WHERE request IS NULL ORDER BY packet')),cancelled)
    if nav.digest(fields.path)!=before:raise ValueError('Index changed during diagnostic export')
    result=dict(status='COMPLETE',source_index_sha256=before,rows=len(fields),
                source_trace_sha256=seal['source_sha256'],display_trace_sha256=seal['display_sha256'],
                packet_namespace='converted_trace_packet_zero_based' if seal['source_sha256']!=seal['display_sha256'] else 'native_trace_packet_zero_based',
                product_verdict='NOT_EVALUATED',scope='diagnostic copies only; not PCIe conformance',
                files={n:dict(sha256=nav.digest(dest/n),bytes=(dest/n).stat().st_size) for n in names})
    large.write_json_bounded(dest/'diagnostic-exports.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',type=Path,help='New folder; default fills deferred copies in the analysis folder')
    args=parser.parse_args(argv);root=args.root.resolve(strict=True)
    import pcie_dense_analysis as dense
    manifest=json.loads((root/'triage-input.json').read_text(encoding='utf-8'))
    dense.validate_inputs(manifest,root)
    fields=disk.Fields(root/'transactions.sqlite')
    try:
        result=export(root,fields,disk.Requests(fields),args.output)
        if nav.digest(fields.path)!=manifest['storage']['sha256']:raise ValueError('Index changed during export')
    finally:fields.close()
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
