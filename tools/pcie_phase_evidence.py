"""Strict bounded-phase log adapter; no root-cause or Hot Plug intent inference."""
from collections import Counter
import re

import pcie_event_coverage as coverage

HEADER = 'PCIE_PHASE_V1|state_cap=4096|link_cap=512|speed_cap=256|dllp_cap=16'
NAMES = ('TLP','DLLP','ORDERED_SET','LINK_CONDITION','EIE','OTHER',
         'LTSSM_CHANGE','SPEED_WIDTH_CHANGE','ACK','NAK','PM','FC','DLLP_OTHER')
CONSTANTS = ('CHANNEL_1','CHANNEL_2','LINK_DOWN','LINK_UP','DETECT','POLLING',
             'CONFIG','L0','RECOVERY','HOT_RESET','DISABLED','UNDEFINED')
CAPS = {'LTSSM_CHANGE':4096, 'LINK_CONDITION':512, 'SPEED_WIDTH_CHANGE':256,
        'ACK':16,'NAK':16,'PM':16,'FC':16,'DLLP_OTHER':16}
# Three-way local check: native constants, CATC main view, independent text
# export. See docs/pcie-vopt-capability-matrix.md and link-mapping.json.
# An unqualified version keeps raw values and cannot create Link Down epochs.
VERIFIED_LINK_ENUMS = {'13.26.0.43': {'LINK_DOWN':1, 'LINK_UP':2}}
DONE = '------- D O N E !!! -------'


def number(text, nullable=False):
    if text == 'NA' and nullable: return None
    if not re.fullmatch(r'\d+', text): raise ValueError('Invalid unsigned native field: '+text)
    return int(text)


def parse(text, native_packet_count):
    if type(native_packet_count) is not int or native_packet_count < 0:
        raise ValueError('Native packet range is not established')
    lines = [line.strip() for line in text.splitlines()]
    if lines.count(HEADER) != 1 or lines.count(DONE) != 1:
        raise ValueError('Expected one phase header and DONE marker')
    if any(re.search(r'Runtime\s+Error|Script.*FAILED|parse error|syntax error|\*\*\*ERROR\*\*\*',l,re.I) for l in lines):
        raise ValueError('Native phase script error')
    constants, counts, events, keys = {}, {}, [], set()
    settings = None
    started = ended = False
    previous = -1
    for line_no, line in enumerate(lines, 1):
        if line == HEADER:
            started = True
            continue
        if not line.startswith('PCIE_PHASE_'): continue
        if not started or ended: raise ValueError('Phase record outside header/end')
        parts=line.split('|');kind=parts[0]
        if kind == 'PCIE_PHASE_SETTINGS' and len(parts)==3 and parts[1]=='nfm_ignore_errors':
            if settings is not None or events or counts: raise ValueError('Duplicate or late LTSSM settings')
            mask=number(parts[2])
            if mask>63: raise ValueError('Unknown NFM ignore bits')
            settings=dict(status='NATIVE_GETTER_REPORTED',nfm_ignore_errors=mask,
                ignored_error_classes=[name for bit,name in enumerate(('TS','FTS','EIEOS','DLLP','TLP','EIOS')) if mask & (1<<bit)],
                gui_equivalence='NOT_ESTABLISHED',source_line=line_no)
        elif kind == 'PCIE_PHASE_CONST' and len(parts)==3:
            name=parts[1]
            if name not in CONSTANTS or name in constants: raise ValueError('Unknown/duplicate constant')
            constants[name]=int(parts[2])
        elif kind == 'PCIE_PHASE_COUNT' and len(parts)==5:
            name=parts[1]
            if name not in NAMES or name in counts: raise ValueError('Unknown/duplicate counter')
            n,first,last=map(number,parts[2:])
            if n and not (0 <= first <= last < native_packet_count): raise ValueError('Counter outside native range')
            if not n and (first or last): raise ValueError('Empty counter has range')
            counts[name]=dict(count=n,first=first if n else None,last=last if n else None)
        elif kind == 'PCIE_PHASE_ROW' and len(parts)==10:
            if counts: raise ValueError('Event emitted after counters')
            _, family,index,display,channel,direction,sec,ns,ps,data=parts
            index=number(index);channel=number(channel)
            if not 0 <= index < native_packet_count or index < previous:
                raise ValueError('Phase indices out of order/range')
            previous=index
            native_time=[number(sec,True),number(ns,True),number(ps,True)]
            if native_time[1] is not None and native_time[1]>=1000000000: raise ValueError('Invalid native ns component')
            if native_time[2] is not None and native_time[2]>=1000: raise ValueError('Invalid native ps component')
            row=dict(kind=family,packet_index=index,time_display=display,time_object=native_time,
                     time_precision='native_components' if all(v is not None for v in native_time[:2]) else 'UNKNOWN',
                     channel=channel,channel_name=direction,direction='UNKNOWN',source_line=line_no,
                     link_identity='UNKNOWN',raw=data)
            values=data.split(',')
            if family=='LTSSM' and len(values)==5 and values[4] in ('idle','packet'):
                row.update(state=number(values[0]),substate=number(values[1]),valid=number(values[2]),
                           subsubstate=number(values[3]),origin=values[4])
                if row['valid'] not in (0,1): raise ValueError('Invalid LTSSM validity')
                counter='LTSSM_CHANGE'
            elif family=='LINK' and len(values)==1:
                row['raw_type']=number(values[0],True);counter='LINK_CONDITION'
            elif family=='SPEED' and len(values)==2:
                row.update(speed_raw=number(values[0]),width=number(values[1]));counter='SPEED_WIDTH_CHANGE'
            elif family=='DLLP' and len(values)==3 and values[0] in CAPS and values[0] not in ('LTSSM_CHANGE','LINK_CONDITION','SPEED_WIDTH_CHANGE'):
                row.update(dllp_class=values[0],raw_type=number(values[1],True),sequence=number(values[2],True));counter=values[0]
            else: raise ValueError('Invalid phase row shape')
            key=(family,index,channel,row.get('origin'))
            if key in keys: raise ValueError('Duplicate phase event')
            keys.add(key);row['counter']=counter;events.append(row)
        elif line=='PCIE_PHASE_END|reason=trace_end': ended=True
        else: raise ValueError('Unrecognized phase record: '+line[:100])
    if not ended or set(counts)!=set(NAMES) or set(constants)!=set(CONSTANTS):
        raise ValueError('Missing phase counters/constants/end')
    if constants['CHANNEL_1']==constants['CHANNEL_2'] or constants['LINK_UP']==constants['LINK_DOWN']:
        raise ValueError('Ambiguous native constant mapping')
    state_names={constants[k]:k for k in CONSTANTS if k not in ('CHANNEL_1','CHANNEL_2','LINK_UP','LINK_DOWN')}
    if len(state_names)!=8: raise ValueError('Ambiguous LTSSM constants')
    emitted=Counter(r['counter'] for r in events)
    for name,cap in CAPS.items():
        if emitted[name]!=min(cap,counts[name]['count']): raise ValueError('Phase counter/detail mismatch: '+name)
    if sum(counts[k]['count'] for k in ('ACK','NAK','PM','FC','DLLP_OTHER'))!=counts['DLLP']['count']:
        raise ValueError('DLLP classification counters disagree')
    for row in events:
        bound=counts[row['counter']]
        if not bound['first'] <= row['packet_index'] <= bound['last']: raise ValueError('Row outside family bounds')
        expected={constants['CHANNEL_1']:'Upstream',constants['CHANNEL_2']:'Downstream'}.get(row['channel'])
        if expected and row['channel_name']==expected: row['direction']=expected
        if row['kind']=='LTSSM': row['state_name']=state_names.get(row['state'],'UNKNOWN')
        if row['kind']=='LINK':
            row['constant_name']={constants['LINK_DOWN']:'LINK_DOWN',constants['LINK_UP']:'LINK_UP'}.get(row['raw_type'],'OTHER')
            row['semantic_status']='RAW_CONSTANT_ONLY'
    return dict(events=events,counts=counts,constants=constants,emitted=dict(emitted),script_done=True,
                ltssm_ignore_settings=settings or 'UNKNOWN_NATIVE_DEFAULT',full_trace_coverage='UNKNOWN')


def load(root, receipt, binding, native_packet_count):
    path=coverage.bound_log(root,'phase.txt',receipt)
    parsed=parse(path.read_text(encoding='utf-8'),native_packet_count)
    ref=dict(path=str(path),sha256=coverage.digest(path))
    if isinstance(parsed['ltssm_ignore_settings'],dict):
        parsed['ltssm_ignore_settings']['evidence_ref']=dict(**ref,line=parsed['ltssm_ignore_settings']['source_line'])
    for row in parsed['events']:
        row.update(source_trace_sha256=binding['source_trace_sha256'],display_trace_sha256=binding['display_trace_sha256'],
                   packet_namespace=binding['packet_namespace'],evidence_ref=dict(**ref,line=row['source_line']))
        enums=VERIFIED_LINK_ENUMS.get(binding['native_version'])
        if row['kind']=='LINK' and enums and all(parsed['constants'][k]==v for k,v in enums.items()):
            row['semantic_status']='VERSION_MAPPING_VERIFIED'
            row['semantic']=row['constant_name'] if row['constant_name'] in enums else 'OTHER'
    families=[]
    for name,cap in CAPS.items():
        c=parsed['counts'][name]
        families.append(coverage.family(binding,name,'_PACKET / explicit phase subscription',c['count'],
            parsed['emitted'].get(name,0),c['first'],c['last'],cap,
            reduction='state changes' if name.endswith('CHANGE') else 'first bounded records',refs=[ref]))
    parsed['coverage']=families
    return parsed
