"""Native Link/Split evidence augments, and never rewrites, G2 associations."""
from collections import Counter, defaultdict
from bisect import bisect_right
import re

import pcie_event_coverage as coverage
from pcie_phase_evidence import number, DONE

HEADER='PCIE_TX_V1|cap=8192'
LEVELS=('packet','link','split')
TYPES=('CFGRD0','CFGWR0','CFGRD1','CFGWR1','CPL','CPLD')
CHANNELS=('CHANNEL_1','CHANNEL_2')
FIELDS=('tlp_type','requester_id','tag','target_id','register','psn','completion_status','transaction_status','metric_packets')


def parse(text,native_packet_count):
    if type(native_packet_count) is not int or native_packet_count<0: raise ValueError('Missing packet bound')
    lines=[l.strip() for l in text.splitlines()]
    if lines.count(HEADER)!=1 or lines.count(DONE)!=1: raise ValueError('Missing transaction header/DONE')
    if any(re.search(r'Runtime\s+Error|parse error|syntax error',l,re.I) for l in lines): raise ValueError('Transaction script error')
    constants={};rows=[];counts={};previous={l:-1 for l in LEVELS};ended=started=False
    for line_number,line in enumerate(lines,1):
        if line==HEADER: started=True;continue
        if not line.startswith('PCIE_TX_'):continue
        if not started or ended: raise ValueError('Transaction record outside header/end')
        parts=line.split('|')
        if parts[0]=='PCIE_TX_CONST' and len(parts)==3:
            name=parts[1]
            if name not in LEVELS+TYPES+CHANNELS or name in constants: raise ValueError('Duplicate/unknown transaction constant')
            constants[name]=number(parts[2])
        elif parts[0]=='PCIE_TX_ROW' and len(parts)==18:
            if counts: raise ValueError('Transaction row after counters')
            ns=parts[1];index=number(parts[2]);channel=number(parts[4]);tm=[number(v,True) for v in parts[6:9]]
            if ns not in LEVELS or index<=previous[ns]: raise ValueError('Duplicate/unordered transaction index')
            if ns=='packet' and index>=native_packet_count: raise ValueError('Packet outside native range')
            if tm[1] is not None and tm[1]>=1000000000 or tm[2] is not None and tm[2]>=1000: raise ValueError('Invalid native time component')
            previous[ns]=index
            values={name:number(value,True) for name,value in zip(FIELDS,parts[9:])}
            rows.append(dict(namespace=ns,index=index,channel=channel,channel_name=parts[5],
                direction='UNKNOWN',
                time_display=parts[3],time_object=tm,time_precision='native_components' if None not in tm[:2] else 'UNKNOWN',
                source_line=line_number,**values))
        elif parts[0]=='PCIE_TX_COUNT' and len(parts)==5:
            ns=parts[1]
            if ns not in LEVELS or ns in counts: raise ValueError('Duplicate/unknown transaction counter')
            n,first,last=map(number,parts[2:])
            if n and last<first or not n and (first or last): raise ValueError('Invalid transaction range')
            counts[ns]=dict(count=n,first=first if n else None,last=last if n else None)
        elif line=='PCIE_TX_END|reason=trace_end':ended=True
        else: raise ValueError('Unrecognized transaction record')
    if not ended or set(constants)!=set(LEVELS+TYPES+CHANNELS) or set(counts)!=set(LEVELS): raise ValueError('Incomplete transaction log')
    if len({constants[n] for n in LEVELS})!=3 or len({constants[n] for n in TYPES})!=6: raise ValueError('Ambiguous transaction enums')
    if constants['CHANNEL_1']==constants['CHANNEL_2']: raise ValueError('Ambiguous transaction channels')
    for ns in LEVELS:
        kept=[r for r in rows if r['namespace']==ns];c=counts[ns]
        if len(kept)!=min(8192,c['count']): raise ValueError('Transaction count mismatch')
        if kept and (kept[0]['index']!=c['first'] or kept[-1]['index']>c['last'] or c['count']<=8192 and kept[-1]['index']!=c['last']): raise ValueError('Transaction bounds mismatch')
    types={constants[k]:k for k in TYPES}
    for row in rows:
        expected={constants['CHANNEL_1']:'Upstream',constants['CHANNEL_2']:'Downstream'}.get(row['channel'])
        if expected and row['channel_name']==expected: row['direction']=expected
        if row['tlp_type'] not in types: raise ValueError('Unsubscribed transaction type')
        row['type_name']=types[row['tlp_type']]
        row['completion_label']={0:'SC',1:'UR',2:'CRS',4:'CA'}.get(row['completion_status'],'UNKNOWN')
        row['link_status_label']={0:'IMPLICIT_ACK',1:'EXPLICIT_ACK',2:'INCOMPLETE'}.get(row['transaction_status'],'UNKNOWN')
    return dict(rows=rows,counts=counts,constants=constants)


def load(root,receipt,binding,native_packet_count):
    path=coverage.bound_log(root,'transactions.txt',receipt)
    result=parse(path.read_text(encoding='utf-8'),native_packet_count)
    ref=dict(path=str(path),sha256=coverage.digest(path))
    for row in result['rows']:
        row.update(source_trace_sha256=binding['source_trace_sha256'],display_trace_sha256=binding['display_trace_sha256'],
                   packet_namespace=binding['packet_namespace'],
                   evidence_ref=dict(**ref,line=row['source_line']))
    families=[]
    for ns in LEVELS:
        c=result['counts'][ns]
        f=coverage.family(binding,'CONFIG_COMPLETION_'+ns,ns+' / config and completion',c['count'],min(8192,c['count']),c['first'],c['last'],8192,refs=[ref])
        f['native_index_namespace']=ns
        families.append(f)
    result['coverage']=families
    return result


def crosscheck(result,phase=None):
    """Associate native starts by exact time and typed identity, never index equality.

    Link/Split index is NOT a Packet index. A match is only an evidence pointer
    to its start; a metric packet count does not identify individual children.
    """
    rows=result['rows'];packets=[r for r in rows if r['namespace']=='packet']
    boundaries=sorted({r['packet_index'] for r in (phase or {}).get('events',[])
        if r.get('semantic_status')=='VERSION_MAPPING_VERIFIED' and r.get('semantic') in ('LINK_DOWN','LINK_UP')})
    def exact_start(row):
        if None in row['time_object'] or row['direction']=='UNKNOWN':return None
        fields=('tlp_type','requester_id','tag','psn')
        if row['type_name'].startswith('CFG'):fields+=('target_id','register')
        if any(row[k] is None for k in fields):return None
        return (tuple(row['time_object']),row['channel'],row['direction'],*(row[k] for k in fields))
    lookup=defaultdict(list)
    for row in packets:
        key=exact_start(row)
        if key is not None:lookup[key].append(row)
    matches=[]
    for row in rows:
        if row['namespace']=='packet':continue
        key=exact_start(row);found=lookup.get(key,[]) if key is not None else []
        matches.append(dict(namespace=row['namespace'],native_index=row['index'],
            packet_index=found[0]['index'] if len(found)==1 else None,
            mapping='EXACT_TYPED_START' if len(found)==1 else 'AMBIGUOUS' if found else 'NOT_ESTABLISHED',
            completion_label=row['completion_label'],link_status_label=row['link_status_label'],metric_packets=row['metric_packets'],
            evidence_ref=row.get('evidence_ref'),packet_ref=found[0].get('evidence_ref') if len(found)==1 else None,
            child_packet_mapping='NOT_ESTABLISHED'))
    groups=defaultdict(list)
    for row in packets:
        if not row['type_name'].startswith('CFG') or row['direction']=='UNKNOWN':continue
        if any(row[k] is None for k in ('requester_id','tag')):continue
        epoch=bisect_right(boundaries,row['index'])
        groups[(row['channel'],epoch,row['requester_id'],row['tag'])].append(row)
    similarities=[]
    for group in groups.values():
        for before,after in zip(group,group[1:]):
            same_target=all(before[k] is not None and before[k]==after[k] for k in ('type_name','target_id','register'))
            similarities.append(dict(first_packet=before['index'],next_packet=after['index'],
                observation='SAME_KEY_SAME_CONFIG_TARGET' if same_target else 'SAME_KEY_DIFFERENT_OR_UNKNOWN_TARGET',
                same_psn=before['psn'] is not None and before['psn']==after['psn'],
                interpretation='OBSERVATION_ONLY',root_cause='NOT_EVALUATED',
                evidence_refs=[before.get('evidence_ref'),after.get('evidence_ref')]))
    return dict(native_starts=matches,request_similarities=similarities,
                association_scope='source-bound typed start; conservative partition at observed Link boundaries',
                limitations=['CRS/UR/CA/SC 是觀察到的原生狀態，不直接判定故障或初始化完成。',
                             '相同 Requester／Tag／目標／PSN 仍不足以區分 RC retry 與 Data Link replay。',
                             '無原生 Split 配對不等於沒有 Completion；cap、過濾與擷取尾端仍需核對。'])


def validate_against_fields(result, fields):
    """Independent G2 export must agree with the retained native Packet rows."""
    types={result['constants'][k] for k in TYPES}
    expected=fields.packet_map if hasattr(fields,'packet_map') else {r['packet_index']:r for r in fields if int(r['tlp_type_hex'],16) in types}
    expected_count=fields.count_types(types) if hasattr(fields,'count_types') else len(expected)
    if result['counts']['packet']['count']!=expected_count:
        raise ValueError('Transaction Packet count contradicts independent G2 fields')
    for row in result['rows']:
        if row['namespace']!='packet':continue
        prior=expected.get(row['index'])
        if prior is None:raise ValueError('Transaction Packet missing from independent G2 fields')
        pairs=((row['tlp_type'],int(prior['tlp_type_hex'],16)),(row['channel_name'],prior['channel']),
               (row['time_display'].strip(),prior['time_display'].strip()),(row['requester_id'],prior['requester_id']),
               (row['tag'],prior['tag']),(row['completion_status'],prior['compl_status']))
        if any(a!=b for a,b in pairs):raise ValueError('Transaction Packet contradicts independent G2 fields')
