"""Bounded second-stage native text, chosen from this import's observations.

Packet windows are evidence, never new fault/ranking rules. A native export
may omit filtered units: exact requested bounds are not a coverage claim.
"""
from decimal import Decimal
import re
import time
from pathlib import Path
import native_navigation as nav

FORMAT='pcie.native-detail/v1'
MAX_WINDOWS=4
BEFORE=16
AFTER=32
MAX_BYTES=2*1024*1024


def propose(locators, summary, count):
    anchors=[]
    for loc in locators[:3]:
        anchors.append(dict(packet_index=loc['packet_index'],reason='candidate'))
    last=(summary or {}).get('last_supported_milestone')
    if last:anchors.append(dict(packet_index=last['anchor']['packet_index'],reason='last_supported_milestone'))
    windows=[]
    for anchor in sorted(anchors,key=lambda a:a['packet_index']):
        index=anchor['packet_index'];nav.validate_index(index,count)
        lo,hi=max(0,index-BEFORE),min(count-1,index+AFTER)
        if windows and lo<=windows[-1]['last']+1:
            windows[-1]['last']=max(hi,windows[-1]['last']);windows[-1]['anchors'].append(anchor)
        else:windows.append(dict(first=lo,last=hi,anchors=[anchor]))
    assert len(windows)<=MAX_WINDOWS
    return windows


def parse(text, work, window):
    file=re.search(r'^\s*File (.+)\.\s*$',text,re.M)
    if not file or Path(file[1]).resolve()!=Path(work).resolve():raise ValueError('Detail belongs to another display trace')
    span=re.search(r'^\s*From Packet #(\d+) to Packet #(\d+)\.',text,re.M)
    if not span or tuple(map(int,span.groups()))!=(window['first'],window['last']):raise ValueError('Native detail range mismatch')
    matches=list(re.finditer(r'^Packet\((\d+)\)\s*',text,re.M));rows=[];previous=-1
    for i,m in enumerate(matches):
        index=int(m[1]);body=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        if not window['first']<=index<=window['last'] or index<=previous:raise ValueError('Unordered/duplicate/outside detail Packet')
        previous=index
        direction=re.match(r'(Upstream|Downstream)\b',body)
        stamp=re.search(r'Time Stamp\(([0-9]+\.[0-9]+)s\)',body)
        rows.append(dict(packet_index=index,direction=direction[1] if direction else 'UNKNOWN',
            timestamp_seconds=stamp[1] if stamp else None,
            timestamp_picoseconds=str(Decimal(stamp[1])*10**12) if stamp else None,
            native_text=body.strip(),source_line=text[:m.start()].count('\n')+1))
    if not rows:raise ValueError('Native detail export contains no Packet rows')
    return rows


def acquire(trace,root,work,binding,windows,cancelled=lambda:False):
    root=Path(root);result=dict(format=FORMAT,**binding,status='complete' if windows else 'not_requested',
        method='ExportToText',windows=[],max_windows=MAX_WINDOWS,before=BEFORE,after=AFTER,
        full_trace_coverage='UNKNOWN',filter_effect='UNKNOWN',packet_count=0)
    for i,window in enumerate(windows):
        if cancelled():raise InterruptedError('Cancelled between native detail exports')
        entry=dict(window,status='unavailable',rows=[]);started=time.monotonic()
        path=root/('detail-window-'+str(i)+'.txt')
        try:
            trace.ExportToText(str(path),window['first'],window['last'])
            if not path.is_file() or path.stat().st_size>MAX_BYTES:raise ValueError('Native detail missing or exceeds byte limit')
            rows=parse(path.read_text(encoding='utf-8-sig'),work,window)
            ref=dict(path=str(path.resolve()),sha256=nav.digest(path))
            for row in rows:row['evidence_ref']=dict(**ref,line=row['source_line'])
            missing=sorted({a['packet_index'] for a in window['anchors']}-{r['packet_index'] for r in rows})
            entry.update(status='partial' if missing else 'complete',rows=rows,evidence_ref=ref,missing_anchors=missing,
                         coverage='EXPORTED_ROWS_ONLY',omitted_packets='UNKNOWN')
            result['packet_count']+=len(rows)
        except Exception as exc:
            entry['error']=str(exc)
            if path.is_file():entry['evidence_ref']=dict(path=str(path.resolve()),sha256=nav.digest(path))
        entry['elapsed_seconds']=time.monotonic()-started;result['windows'].append(entry)
    if any(w['status']!='complete' for w in result['windows']):result['status']='partial'
    return result


def load(root,receipt,binding,expected):
    import json
    root=Path(root).resolve();path=root/'detail-windows.json'
    if nav.digest(path)!=receipt['sha256']:raise ValueError('Native detail receipt changed')
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('format')!=FORMAT or any(data.get(k)!=v for k,v in binding.items()):raise ValueError('Native detail source mismatch')
    actual=[{k:w[k] for k in ('first','last','anchors')} for w in data['windows']]
    if actual!=expected:raise ValueError('Native detail windows differ from this analysis')
    if data.get('full_trace_coverage')!='UNKNOWN' or data.get('filter_effect')!='UNKNOWN':
        raise ValueError('Unsupported detail coverage claim')
    total=0
    for window in data['windows']:
        if window.get('status') not in ('complete','partial','unavailable'):raise ValueError('Invalid window state')
        ref=window.get('evidence_ref')
        if window['status']!='unavailable' and not ref:raise ValueError('Missing detail evidence')
        if window['status']=='unavailable' and window['rows']:raise ValueError('Unavailable detail has rows')
        if ref:
            file=Path(ref['path']).resolve(strict=True)
            if not file.is_relative_to(root) or nav.digest(file)!=ref['sha256']:raise ValueError('Detail evidence escaped import or changed')
            if window['status'] in ('complete','partial'):
                if file.stat().st_size>MAX_BYTES:raise ValueError('Detail exceeds byte limit')
                rows=parse(file.read_text(encoding='utf-8-sig'),root/'display-working.pex',window)
                for row in rows:row['evidence_ref']=dict(**ref,line=row['source_line'])
                if rows!=window['rows']:raise ValueError('Detail rows differ from native evidence')
                missing=sorted({a['packet_index'] for a in window['anchors']}-{r['packet_index'] for r in rows})
                if window.get('missing_anchors')!=missing or window['status']!=('partial' if missing else 'complete'):
                    raise ValueError('Detail anchor status mismatch')
                total+=len(rows)
    status='not_requested' if not expected else 'partial' if any(w['status']!='complete' for w in data['windows']) else 'complete'
    if data.get('status')!=status or data.get('packet_count')!=total or receipt.get('status')!=status or receipt.get('packet_count')!=total:
        raise ValueError('Detail aggregate mismatch')
    return data
