"""Automation-first PD data; preserve units, ambiguous columns and packet refs."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import bisect
from pathlib import Path
from usb3_triage import integer
from usb_triage_model import target, seconds

SOP={0:'No framing',1:'SOP',2:"SOP'",3:"SOP''",4:"SOP' Debug",5:"SOP'' Debug",6:'Hard Reset',7:'Cable Reset'}
MESSAGE={1:'GoodCRC',3:'Accept',4:'Reject',6:'PS Ready',12:'Wait',13:'Soft Reset',33:'Source Cap',34:'Request',47:'Vendor Defined',251:'Hard Reset',252:'Cable Reset'}


def ns(text):
    if not text or not text.strip():return None
    try:
        value=Decimal(text.strip())*1000000000
        if not value.is_finite() or value<0 or value!=value.to_integral_value() or value>9223372036854775807:raise ValueError('Invalid native PD timestamp')
        return int(value)
    except InvalidOperation as ex:raise ValueError('Invalid native PD timestamp') from ex


def headers(raw):
    if raw.get('format')!='usb-protocol-data/v1' or raw.get('error') or not all(raw.get(k) is True for k in ('integrity_unchanged','script_unchanged','native_exited')) or (raw.get('run_result'),raw.get('finished_result'),raw.get('finished_count'))!=(2,2,1):
        raise ValueError('PD header acquisition incomplete')
    packets={};end=None
    for text in raw['reports']:
        f=text.split('|');kind=f[0]
        if kind not in ('PDBASE','PDHDR','PDVDM','PD-END'):continue
        if end is not None:raise ValueError('PD row after end marker')
        if kind=='PD-END':
            if len(f)!=3:raise ValueError('Malformed PD end marker')
            end=tuple(map(integer,f[1:]));continue
        if kind=='PDBASE':
            if len(f)!=7:raise ValueError('Malformed PD packet')
            i,sec,nano,ch,typ,sender=map(integer,f[1:])
            if i in packets or nano>=1000000000 or i>2147483647:raise ValueError('Invalid/duplicate PD packet identity')
            packets[i]=dict(index=i,timestamp_ns=sec*1000000000+nano,channel=ch,packet_type_raw=typ,
                            sender_port_raw=sender,message=MESSAGE.get(typ,'PD type '+str(typ)))
        elif kind=='PDHDR':
            if len(f)!=9:raise ValueError('Malformed PD header')
            i,sop,rev,msg,dr,pr,obj,length=map(integer,f[1:]);p=packets.get(i)
            if p is None or 'sop_raw' in p or sop>7 or rev>3 or msg>7 or dr>1 or pr>1 or obj>7:
                raise ValueError('PD header without unique valid packet')
            p.update(sop_raw=sop,sop=SOP[sop],revision_raw=rev,msg_id=msg,data_role_raw=dr,power_role_raw=pr,object_count=obj,buffer_len=length)
        else:
            if len(f)!=5:raise ValueError('Malformed VDM decoded fields')
            p=packets.get(integer(f[1]))
            if p is None or 'vdm' in p:raise ValueError('VDM without unique PD packet')
            p['vdm']=dict(vendor=f[2] or None,command=f[3] or None,command_type=f[4] or None)
    if end is None or end[1]!=len(packets) or not end[0]>=end[1] or end[1]>50000:raise ValueError('PD header count reconciliation failed')
    for p in packets.values():
        if p['packet_type_raw'] in MESSAGE and p['packet_type_raw'] not in (251,252) and 'sop_raw' not in p:
            raise ValueError('Supported PD message missing required header')
    return sorted(packets.values(),key=lambda p:(p['timestamp_ns'],p['index'])),dict(pd_packet_events=end[0],emitted_packets=end[1],header_limit=50000,headers_truncated=end[1]<end[0])


def cell(row,name):
    values=list(dict.fromkeys(value.strip() for key,value in row['cells'] if key==name and value.strip()))
    return values[0] if len(values)==1 else None


def csv_rows(body,level):
    # Duplicate/empty header names are kept as ordered cells. Never DictReader's
    # last-column-wins behavior for repeated PDO/VDM fields.
    text=body.decode('utf-16') if body.startswith((b'\xff\xfe',b'\xfe\xff')) else body.decode('utf-8-sig')
    reader=csv.reader(io.StringIO(text,newline=''));names=next(reader,None)
    identity='Transaction' if level==1 else 'Transfer'
    if not names or names.count(identity)!=1 or 'Rec Chan' not in names or 'Time Stamp' not in names:raise ValueError('Missing native PD CSV identity columns')
    result=[];seen=set()
    for values in reader:
        if not any(values):continue
        if len(values)!=len(names):raise ValueError('Truncated native PD CSV row')
        row={'cells':list(zip(names,values)),'level':level}
        if cell(row,'Rec Chan')!='PD':continue
        i=integer(cell(row,identity) or '',high=2147483647)
        if i in seen:raise ValueError('Duplicate native PD group')
        seen.add(i);row.update(index=i,timestamp_ns=ns(cell(row,'Time Stamp')),duration_display=cell(row,'Time'),
                              data_role=cell(row,'DR'),power_role=cell(row,'PR') or cell(row,'Dir'),status=cell(row,'Status'))
        if level==1:row['message']=cell(row,'Msg Type')
        else:
            row['message']=next((n for n in ('Power Negotiation','Get Sink Cap','Discover Identity','Discover SVIDs','Discover Modes','Enter Mode','Exit Mode','DP Status','DP Configure') if cell(row,n)),None)
            row['vendor']=cell(row,'Vendor ID')
        result.append(row)
    return result


def load(directory):
    directory=Path(directory);meta=json.loads((directory/'raw-result.json').read_text(encoding='utf-8-sig'))
    if meta.get('format')!='pd-native-data/v1' or meta.get('error') or meta.get('integrity_unchanged') is not True or meta.get('native_exited') is not True:
        raise ValueError('PD Automation acquisition incomplete')
    header_body=(directory/'headers/raw-result.json').read_bytes()
    if hashlib.sha256(header_body).hexdigest()!=meta['header_raw_sha256']:raise ValueError('PD header evidence changed')
    raw=json.loads(header_body.decode('utf-8-sig'))
    if raw['trace_sha256']!=meta['trace_sha256']:raise ValueError('PD source hash mismatch')
    packets,coverage=headers(raw);issues=[];tables={1:[],3:[]};levels=set()
    for export in meta['exports']:
        level=export['level']
        if level not in tables or level in levels:raise ValueError('Invalid PD export level')
        levels.add(level)
        filename='transactions.csv' if level==1 else 'transfers.csv'
        if export['file']!=filename:raise ValueError('Unexpected PD evidence path')
        if export['state']!='returned':issues.append(filename+': '+export['state']);continue
        body=(directory/filename).read_bytes()
        if hashlib.sha256(body).hexdigest()!=export['identity']['sha256'] or len(body)!=export['identity']['size']:raise ValueError('PD CSV evidence changed')
        tables[level]=csv_rows(body,level)
    if levels!={1,3}:issues.append('Native group export level missing')
    bytime=defaultdict(list)
    for p in packets:bytime[p['timestamp_ns']].append(p)
    for row in tables[1]+tables[3]:
        matches=bytime.get(row['timestamp_ns'],[])
        # Exact start timestamp and unique PD packet qualify a navigation anchor;
        # this is not a complete group-child membership reconstruction.
        row['packet_anchor']=matches[0]['index'] if len(matches)==1 else None
        row['sop']=matches[0].get('sop') if len(matches)==1 else None
        row['sop_raw']=matches[0].get('sop_raw') if len(matches)==1 else None
        row['role_applicability']='SOP' if row['sop_raw']==1 else 'unqualified' if row['sop_raw'] is None else 'cable_or_other'
        if row['role_applicability']!='SOP':row.update(data_role=None,power_role=None)
    missing_times=sum(r['timestamp_ns'] is None for r in tables[1]+tables[3])
    if missing_times:issues.append(str(missing_times)+' native groups have no timestamp')
    unmatched=sum(r['packet_anchor'] is None for r in tables[1]+tables[3])
    if unmatched:issues.append(str(unmatched)+' native group starts have no unique PD Packet anchor')
    if coverage['pd_packet_events']==0 and (tables[1] or tables[3]):issues.append('Native CSV contains PD groups but packet evidence is missing')
    if coverage['pd_packet_events'] and not (tables[1] or tables[3]):issues.append('PD packets observed without parsed native PD groups')
    coverage.update(transactions=len(tables[1]),transfers=len(tables[3]),missing_group_timestamps=missing_times,unmatched_group_starts=unmatched,
                    group_exports='Automation full native level range; display profile may filter',capture_start_known=False,capture_end_known=False)
    return dict(protocol='PD',trace_sha256=meta['trace_sha256'],state='partial' if coverage['headers_truncated'] or issues else 'analyzed' if coverage['pd_packet_events'] else 'not_observed',
                scope='PD 基本協商與 Structured VDM；其他訊息僅保留原生證據',coverage=coverage,
                packets=packets,transactions=tables[1],transfers=tables[3],limitations=issues+[
                'CSV 原生群組沿用 LeCroy；Packet anchor 只核對起始時間，未建立完整 child membership。',
                '保留重複／空白欄名及原生帶單位值；不能把電流／功率並列顯示直接當成已選 PDO 的單位。',
                '捕獲起訖未知；不含完整 payload／extended messages、PPS／EPR／role-swap 合規或根因判定。'])


def discover(data):
    """Structural investigation policies, not PD compliance or timer rules.

    Native transactions already fold wire retries. A separate neutral flow list
    exposes evidence without promoting a single NAK to a suspect candidate.
    """
    analysis={k:data[k] for k in ('protocol','state','scope','coverage','limitations')}
    analysis['limitations']=list(data['limitations'])+[
        '僅 SOP 基本協商／VDM 結構導引；不套用任意 timeout，未驗證 CRC／電氣／完整合規。',
        '已觀察流程是中性證據入口，不列入候選數；附近 Transaction 不等於完整群組成員。']
    analysis.update(rule_version='pd-negotiation-vdm-guidance/1',episode_count=0,candidates=[],observations=[])
    packets=data['packets'];byindex={p['index']:p for p in packets}
    times=[p['timestamp_ns'] for p in packets]
    tx=sorted(data['transactions'],key=lambda r:(r['timestamp_ns'] is None,r['timestamp_ns'] or 0,r['index']))
    transfers=sorted(data['transfers'],key=lambda r:(r['timestamp_ns'] is None,r['timestamp_ns'] or 0,r['index']))
    def anchor(r):return byindex.get(r.get('packet_anchor'))
    def qualified(p):return p is not None and p.get('sop_raw')==1 and p.get('sender_port_raw') in (1,2)
    def ctx(r):
        p=anchor(r) or {};role=' / '.join(str(v) for v in (r.get('data_role'),r.get('power_role')) if v) or '角色未知'
        values=[f'{k}={v.strip()}' for k,v in r['cells'] if v.strip() and k not in ('Rec Chan','Transaction','Transfer','Time Stamp')]
        return dict(index=('Transfer ' if r['level']==3 else 'Transaction ')+str(r['index']),timestamp_ns=r['timestamp_ns'],
                    channel=str(p.get('channel','未知'))+' / '+str(r.get('sop') or 'SOP 未知'),message=r.get('message') or '原生訊息未知',
                    result=(r.get('status') or '未提供完成狀態')+' · '+role,detail='; '.join(values),native=r)
    def make(rows,title,why,next_step):
        first=rows[0];p=anchor(first);ts=[target('PD',first['level'],first['index'],first['timestamp_ns'],p['channel'])]
        visible=rows if len(rows)<=12 else rows[:6]+rows[-6:]
        for r in visible:
            q=anchor(r)
            if q and len(ts)<16:
                t=target('PD',0,q['index'],q['timestamp_ns'],q['channel'])
                if t not in ts:ts.append(t)
        return dict(title=title,start_ns=first['timestamp_ns'],end_ns=rows[-1]['timestamp_ns'],native_targets=ts,
                    facts=[f'本區段關聯 {len(rows)} 筆原生群組；最多顯示首尾 12 筆。']+[f"{r['message'] or '原生流程'}：{('Transfer' if r['level']==3 else 'Transaction')} {r['index']}，{r.get('status') or '完成狀態未提供'}。" for r in visible],
                    reasons=[why],next_step=next_step,evidence_gaps=['起訖與完整 payload／CRC 狀態未核實；不能據此判定韌體故障或合規。'],context=[ctx(r) for r in visible],evidence_completeness='partial')
    # Neutral native flows: first group plus nearby transactions, bounded by the
    # next native transfer start. This is labelled context, never membership.
    eligible=[r for r in transfers if qualified(anchor(r)) and r['timestamp_ns'] is not None and r.get('message')]
    analysis['observation_count']=len(eligible)
    for r in eligible[:24]:
        p=anchor(r);pos=transfers.index(r);end=transfers[pos+1]['timestamp_ns'] if pos+1<len(transfers) else None
        nearby=[t for t in tx if t['timestamp_ns'] is not None and t['timestamp_ns']>=r['timestamp_ns'] and (end is None or t['timestamp_ns']<end) and qualified(anchor(t)) and anchor(t)['channel']==p['channel']][:12]
        flow=make([r],(r.get('vendor')+' · ' if r.get('vendor') else '')+r['message'],
                  '已觀察的原生流程，供人工核對；未因單次 ACK／NAK／Cap Mismatch 提升為候選。',
                  '先核對原生 Transfer 與起始 Packet，再看前後交易中的訊息、角色與帶單位欄位；單次拒絕需對照測試情境，不直接當故障。')
        flow['context']+=[ctx(t) for t in nearby]
        flow['facts']+=['SOP='+p['sop']+'；原生資料如下，空白欄位維持未知。']
        start_tx=next((t for t in nearby if t['packet_anchor']==p['index']),r)
        flow['facts']+=['原生角色：DR='+str(start_tx.get('data_role') or '未知')+'；PR='+str(start_tx.get('power_role') or '未知')+'。']
        unit_values=[k+'='+v for k in ('Voltage','Max Cur','Opr Cur','Opr Pwr','Min Volt','Max Volt') if (v:=cell(r,k))]
        if unit_values:flow['facts'].append('原生帶單位欄位：'+'；'.join(unit_values)+'。未重算 PDO／RDO 數值。')
        # Match a VDM response only within this flow's neighbouring interval,
        # same channel/SOP/vendor/command, opposite qualified sender.
        v=p.get('vdm',{})
        if v.get('command_type')=='REQ':
            for q in packets[bisect.bisect_right(times,p['timestamp_ns']):]:
                if end is not None and q['timestamp_ns']>=end:break
                if q['channel']!=p['channel']:continue
                if q['packet_type_raw'] not in (1,47):break
                w=q.get('vdm',{})
                if w.get('command_type')=='REQ':break
                if qualified(q) and q['sop_raw']==p['sop_raw'] and q['sender_port_raw']!=p['sender_port_raw'] and w.get('vendor')==v.get('vendor') and w.get('command')==v.get('command') and w.get('command_type') in ('ACK','NAK','BUSY'):
                    flow['native_targets'].append(target('PD',0,q['index'],q['timestamp_ns'],q['channel']));break
        analysis['observations'].append(flow)
    if data['state']!='analyzed':
        analysis['limitations'].append('資料不完整，停用依賴後續未見完成／重複序列的候選規則。')
        return analysis
    candidates=[];pending={};cursor=0
    for r in tx:
        p=anchor(r)
        if not qualified(p):pending.clear();continue
        endpos=bisect.bisect_left(times,p['timestamp_ns'])
        if any(q['packet_type_raw'] in (13,251,252) for q in packets[cursor:endpos]):pending.clear()
        cursor=endpos
        ch=p['channel'];m=r.get('message');state=pending.get(ch)
        if m=='Request':
            if state and state['accepted'] and state['sender']==p['sender_port_raw']:
                state['rows'].append(r);state['restarted']=True;state['accepted']=False
            else:pending[ch]=dict(rows=[r],sender=p['sender_port_raw'],accepted=False,restarted=False)
        elif m=='Accept' and state and p['sender_port_raw']!=state['sender']:
            state['accepted']=True;state['rows'].append(r)
        elif m in ('GoodCRC','Vendor Defined'):
            continue
        else:pending.pop(ch,None) # includes PS Ready, Reject, Wait and reset/role changes
    if any(q['packet_type_raw'] in (13,251,252) for q in packets[cursor:]):pending.clear()
    for state in pending.values():
        if state['restarted']:
            candidates.append(make(state['rows'],'Request 接受後再次提出協商',
                '不同原生 Transaction 形成 Request→Accept→Request；不是把同一訊息的 wire retry 重複計數。',
                '從第一筆 Request 查看接受後的後續交易，確認是否有 PS Ready、重新協商或角色／連線改變；若後段未擷取，先補資料，再對照測試預期。'))
    # Explicit repeated VDM outcomes; any intervening non-VDM/non-GoodCRC
    # packet is a conservative epoch boundary (including reset/role changes).
    negative={};cursor=0
    for r in transfers:
        p=anchor(r)
        if p is None:negative.clear();continue
        endpos=bisect.bisect_left(times,p['timestamp_ns'])
        if any(q['packet_type_raw'] not in (1,47) for q in packets[cursor:endpos]):negative.clear()
        cursor=endpos
        v=p.get('vdm',{})
        if not qualified(p) or v.get('command_type')!='REQ' or not v.get('vendor') or not v.get('command'):
            negative.clear();continue
        key=(p['channel'],p['sop_raw'],p['sender_port_raw'],v['vendor'],v['command'])
        if r['status']=='ACKed':negative.pop(key,None)
        elif r['status'] in ('NAKed','BUSY'):negative.setdefault(key,[]).append(r)
        else:negative.pop(key,None)
    if any(q['packet_type_raw'] not in (1,47) for q in packets[cursor:]):negative.clear()
    for rows in negative.values():
        if len(rows)>1:
            candidates.append(make(rows,'重複 '+rows[0]['message']+' 未獲接受',
                '同一 SOP／發送端／vendor／command 的不同原生 Transfer 多次回覆 NAK／BUSY；同段合併為一個候選。',
                '先展開第一次 VDM 請求與回覆，核對 command／mode／回覆，再比較後續重試；確認測試是否允許拒絕，並向後查看是否恢復 ACK。'))
    candidates.sort(key=lambda c:c['start_ns'])
    analysis.update(episode_count=len(candidates),candidates=candidates[:3])
    return analysis
