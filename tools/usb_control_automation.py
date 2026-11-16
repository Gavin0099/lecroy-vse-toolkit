"""Project native transfer CSV into the same USB control triage engine (no VSE)."""
import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import usb_control_triage as engine

REQUESTS = {'GET_STATUS':0,'CLEAR_FEATURE':1,'SET_FEATURE':3,'SET_ADDRESS':5,
            'GET_DESCRIPTOR':6,'SET_DESCRIPTOR':7,'GET_CONFIGURATION':8,
            'SET_CONFIGURATION':9,'GET_INTERFACE':10,'SET_INTERFACE':11,'SYNCH_FRAME':12}
TYPES = {'DEVICE':1,'CONFIGURATION':2,'STRING':3,'DEVICE_QUALIFIER':6,
         'OTHER_SPEED_CONFIGURATION':7,'BOS':15}


def optional_number(text):
    if not text or not text.strip():
        return None
    s=text.strip()
    if re.fullmatch(r'0x[0-9a-fA-F]+',s):
        return int(s,16)
    return int(s) if re.fullmatch(r'\d+',s) else None


def value_number(text):
    value=optional_number(text)
    if value is not None:
        return value
    m=re.fullmatch(r'([A-Z_]+) type(?:, Index (\d+))?',text or '')
    if m and m[1] in TYPES:
        return (TYPES[m[1]]<<8) | int(m[2] or '0')
    return None


def csv_projection(manifest_path):
    p=Path(manifest_path)
    m=json.loads(p.read_text(encoding='utf-8-sig'))
    if m.get('adapter')!='native_transfer_csv' or m.get('automation_completed') is not True or m.get('error')!='':
        raise engine.InputError('Automation CSV acquisition not established')
    for k in ('source_unchanged','working_copy_unchanged','working_copy_readonly'):
        if m.get('integrity',{}).get(k) is not True:
            raise engine.InputError('Automation protected-copy check missing')
    if not re.fullmatch(r'[0-9a-fA-F]{64}',m.get('trace_sha256','')):
        raise engine.InputError('Missing trace identity')
    csv_path=p.parent/'transfers.csv'
    if hashlib.sha256(csv_path.read_bytes()).hexdigest()!=m.get('csv_sha256'):
        raise engine.InputError('Native CSV identity mismatch')
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'Transfer','Sp','Control','Ad','Ep','bRequest','wValue','wIndex','Time Stamp'}.issubset(reader.fieldnames or []):
            raise engine.InputError('Native CSV required columns missing')
        rows=list(reader)
    events=[];unsupported=0
    for row in rows:
        if None in row:
            raise engine.InputError('Malformed native CSV row')
        # Ignore Marker entirely. Class/vendor numeric requests stay unclassified.
        if not (row.get('Control') or '').startswith('Control:'):
            continue
        if row.get('Sp') not in ('H','F','L'):
            unsupported+=1
            continue
        request=REQUESTS.get(row.get('bRequest'))
        value=value_number(row.get('wValue'))
        raw_index=row.get('wIndex','')
        lang=re.fullmatch(r'Language ID (0x[0-9A-Fa-f]+)',raw_index)
        request_index=optional_number(lang[1] if lang else raw_index)
        timestamp=row.get('Time Stamp','')
        if not re.fullmatch(r'\d+(?:\.\d{1,9})?',timestamp):
            raise engine.InputError('Native CSV timestamp unavailable')
        ns=int(Decimal(timestamp)*1_000_000_000)
        index=optional_number(row.get('Transfer'))
        address=optional_number(row.get('Ad'));endpoint=optional_number(row.get('Ep'))
        if index is None or address is None or endpoint is None or address>127 or endpoint>15:
            raise engine.InputError('Native transfer identity unavailable')
        if events and (index<=events[-1]['index'] or ns<events[-1]['timestamp_ns']):
            raise engine.InputError('Native CSV order/identity mismatch')
        # A native standard name is semantic classification, not recovered bmRequestType.
        classified=request is not None and (request!=6 or value is not None)
        e={'index':index,'seconds':ns//1_000_000_000,'nanoseconds':ns%1_000_000_000,
           'timestamp_ns':ns,'duration_ns':None,'duration_seconds':None,'duration_nanoseconds':None,
           'channel':1,'speed':{'H':0,'F':1,'L':2}[row['Sp']],'address':address,'endpoint':endpoint,
           'completed':{'NO':0,'YES':1}.get(row.get('Cplt')),'halted':None,'error':None,
           'direction':1 if row['Control']=='Control:GET' else 0 if row['Control']=='Control:SET' else None,
           'request_type':0 if classified else None,'recipient':None,'request':request,
           'value':value,'request_index':request_index,'requested_length':optional_number(row.get('wLength')),
           'native_payload_length':None,'native_prefix_hex':None,'setup_bytes_match':False,
           'data_length':None,'data_prefix_hex':None,'packet_refs':None,
           'semantic_classification_source':'native_decoded_request_name' if classified else 'unknown',
           'native_insufficient_data_text':row.get('Not Enough Data','')}
        events.append(e)
    return {'trace_sha256':m['trace_sha256'].lower(),'extractor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'events':events,'visited_transfers':len(rows),'eligible_controls':len(events),
            'unsupported_controls':unsupported,'truncated':False}


def analyze_file(source, output):
    data=csv_projection(source)
    model=engine.discover(data)
    model['analysis_inputs']=['native_transfer_csv']
    model['source_adapter']='Automation ExportToCsv level 3'
    model['analysis_source_sha256']=hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest()
    model['adapter_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    model['missing_fields']=['raw bmRequestType/recipient','complete duration','per-row completion when Cplt blank',
                             'halted/error flags','actual payload bytes and response length']
    model['limitations'].append('Automation CSV 投影：空白欄位保持未知；Not Enough Data 不等於已證明的零資料回應。未測試的 Automation 介面可能補足這些資料。')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if any((output/name).exists() for name in ('inspection.json','report.html')):
        raise engine.InputError('Refusing report overwrite')
    (output/'inspection.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'report.html').write_text(engine.render(model),encoding='utf-8')
    return model


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        model=analyze_file(a.input,a.output)
        print(json.dumps({'backend':'Automation','status':model['status'],'candidates':len(model['candidates'])},ensure_ascii=False))
        return 0
    except (OSError,ValueError,TypeError) as exc:
        print(json.dumps({'status':'error','reason':str(exc)},ensure_ascii=False));return 1


if __name__=='__main__':
    raise SystemExit(main())
