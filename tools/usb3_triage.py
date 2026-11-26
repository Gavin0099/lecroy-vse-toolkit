"""USB3 Link/LFPS data and bounded single-trace guidance. No C5 baseline."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict
from usb_triage_model import target, seconds


def integer(text, low=0, high=9223372036854775807):
    if not isinstance(text,str) or not text.isascii() or not text.isdecimal():
        raise ValueError('Non-integer native USB3 field')
    n=int(text)
    if not low<=n<=high:raise ValueError('USB3 field outside range')
    return n


def normalize(raw):
    if raw.get('format')!='usb-protocol-data/v1' or raw.get('error') or not all(raw.get(k) is True for k in ('integrity_unchanged','script_unchanged','native_exited')):
        raise ValueError('USB3 acquisition or integrity incomplete')
    if (raw.get('run_result'),raw.get('finished_result'),raw.get('finished_count'))!=(2,2,1):
        raise ValueError('USB3 engine did not complete once')
    events=[];summary=None;seen=set();counts={'U02':0,'U03':0,'U3LT':0}
    for line in raw['reports']:
        if not isinstance(line,str):raise ValueError('Invalid native report')
        f=line.split('|');kind=f[0]
        if kind=='USB3-END':
            if summary is not None or len(f)!=14:raise ValueError('Invalid/duplicate USB3 end marker')
            summary=[integer(x) for x in f[1:]];continue
        if kind not in counts:continue
        if summary is not None:raise ValueError('USB3 row after end marker')
        if len(f)!={'U02':13,'U03':14,'U3LT':6}[kind]:raise ValueError('Malformed USB3 record')
        index,sec,ns,channel,speed=map(integer,f[1:6]);integer(f[3],high=999999999)
        if index>2147483647:raise ValueError('Native index exceeds navigation range')
        key=(kind,index,channel)
        if key in seen:raise ValueError('Duplicate native USB3 record')
        seen.add(key);counts[kind]+=1
        e=dict(kind={'U02':'LINK_CMD','U03':'LFPS','U3LT':'LTSSM_ANCHOR'}[kind],index=index,
               timestamp_ns=sec*1000000000+ns,channel=channel,speed_raw=speed,level=0)
        if kind=='U02':
            cmd,info,crc,repinfo,repcrc=map(integer,f[6:11])
            if info>2047 or repinfo>2047 or crc>31 or repcrc>31:raise ValueError('Invalid LC bit width')
            e.update(name=f[11],mode=f[12],raw_type=cmd,info_raw=info,crc5_raw=crc,replica_info_raw=repinfo,replica_crc5_raw=repcrc)
        elif kind=='U03':
            typ,dur,dsec,dns,pattern,start=map(integer,f[6:12]);integer(f[9],high=999999999)
            e.update(name=f[12],mode=f[13],raw_type=typ,duration_raw_ns=dur,duration_ns=dsec*1000000000+dns,pattern_type_raw=pattern,starts_pattern_raw=start)
        else:e.update(name='LTSSM anchor; exact state unknown')
        if kind!='U3LT' and ((speed,e['mode']) not in ((4,'SS'),(5,'SSP')) or not e['name']):
            raise ValueError('Unsupported USB3 mode/name')
        events.append(e)
    if summary is None:raise ValueError('Missing USB3 end marker')
    visited,ss,lc,lf,lt,lco,lfo,lto,unknown,pd,cc,lastsec,lastns=summary
    if counts!={'U02':lco,'U03':lfo,'U3LT':lto} or lco>lc or lfo>lf or lto>lt or lco+lfo>300000 or lto>64:
        raise ValueError('USB3 count reconciliation failed')
    if ss>visited or pd>visited or cc>visited or lastns>=1000000000:
        raise ValueError('USB3 coverage counters invalid')
    events.sort(key=lambda e:(e['timestamp_ns'],e['index'],e['channel'],e['kind']))
    cutoff=lco+lfo<lc+lf
    partial=cutoff or unknown>0
    coverage=dict(visited_packet_events=visited,observed_ss_ssp=ss,link_total=lc,lfps_total=lf,ltssm_total=lt,
                  emitted_link=lco,emitted_lfps=lfo,emitted_ltssm_anchors=lto,record_limit=300000,
                  truncated=cutoff,unknown_selected_mode=unknown,pd_packet_events=pd,cc_events=cc,
                  last_visible_ns=lastsec*1000000000+lastns,filters='Packet level, all channels/events delivered by VSE display profile; bad-CRC included',
                  capture_start_known=False,capture_end_known=False)
    return dict(protocol='USB3',state='partial' if partial else 'analyzed' if lc or lf or lt else 'not_observed',
                trace_sha256=raw['trace_sha256'],scope='USB3 Link Command / LFPS；LTSSM 僅位置，不含精確 state 或 bulk/streams',
                coverage=coverage,events=events,limitations=['捕獲起訖與完整性未知；未觀察到後續不等於裝置未回應。',
                'LTSSM anchor 可與其他 Packet 共用編號，不能推算 state。',
                '速度計數僅供盤點；未見 Link／LFPS／LTSSM 時，不以單一 Packet 速度宣稱本範圍已分析。']+(['已達輸出上限，僅分析保存的前段事件。'] if cutoff else [])+(['有未支援速度的選定事件。'] if unknown else []))


def discover(data):
    """Prioritize compound unrecovered tails, without a timer or PASS baseline.

    LGOOD/LCRD merely mark visible link traffic; they do not prove application
    success. A native illegal LFPS, polling, or one Wake/Reset alone never
    creates a candidate. Missing output cannot establish an unrecovered tail.
    """
    analysis={k:v for k,v in data.items() if k not in ('events','trace_sha256')}
    analysis.update(candidates=[],episode_count=0,rule_version='usb3-link-lfps-guidance/1')
    if data['state']!='analyzed':
        if data['state']=='partial':analysis['limitations']=data['limitations']+['資料有截斷／未知速度，未用「後續未見 Link Command」規則產生候選；請先補足資料範圍。']
        return analysis
    tails=defaultdict(list)
    preceding={}
    for e in data['events']:
        channel=e['channel']
        if e['kind']=='LINK_CMD' and e['name'].startswith(('LGOOD','LCRD')):
            tails[channel]=[];preceding[channel]=e
        elif e['kind']=='LFPS':tails[channel].append(e)
    candidates=[]
    for channel,events in tails.items():
        resets=[e for e in events if e['name']=='LFPS_RESET']
        wakes=[e for e in events if e['name'].startswith('LFPS_WAKE')]
        bad=[e for e in events if e['name']=='LFPS_ILLEGAL']
        polling=[e for e in events if e['name']=='LFPS_POLLING']
        prior=preceding.get(channel)
        # These are structural combinations, not protocol violation thresholds.
        def before_reset(seq):
            if not seq:return None
            r=next((r for r in resets if seq[0]['timestamp_ns']<r['timestamp_ns']),None)
            return (seq[0],r) if r else None
        wake_reset=before_reset(wakes);bad_reset=before_reset(bad)
        reset_polling=(resets[0],polling[-1]) if prior and resets and polling and resets[0]['timestamp_ns']<polling[-1]['timestamp_ns'] else None
        bad_polling=(bad[0],polling[-1]) if prior and bad and polling and bad[0]['timestamp_ns']<polling[-1]['timestamp_ns'] else None
        if not wake_reset and not bad_reset and len(resets)<2 and not reset_polling and not bad_polling:continue
        pairs=[p for p in (wake_reset,bad_reset,reset_polling,bad_polling) if p]
        anchor=min((p[0] for p in pairs),key=lambda e:e['timestamp_ns']) if pairs else resets[0]
        relevant=[e for e in events if e['timestamp_ns']>=anchor['timestamp_ns']]
        names=Counter(e['name'] for e in relevant)
        if bad_reset:title='LFPS 非法解碼後出現 Reset，後續未見 Link Command'
        elif wake_reset:title='Wake 後出現 Reset，後續未見 Link Command'
        elif len(resets)>=2:title='重複 Reset，後續未見 Link Command'
        elif reset_polling:title='Link 流量後出現 Reset 與 Polling，後續未見 Link Command'
        else:title='Link 流量後有非法 LFPS 解碼與 Polling，後續未見 Link Command'
        essential=[anchor]+[e for pair in pairs for e in pair]+[e for e in resets if e['timestamp_ns']>=anchor['timestamp_ns']][:4]+bad[:2]+polling[:2]+relevant[-3:]
        if prior:essential.insert(0,prior)
        unique={(e['kind'],e['index'],e['channel']):e for e in essential}
        context=[]
        for e in sorted(unique.values(),key=lambda e:e['timestamp_ns']):
            context.append(dict(index=e['index'],timestamp_ns=e['timestamp_ns'],channel=e['channel'],message=e['name'],
                                result='原生解碼觀察',detail=('duration '+str(e['duration_ns'])+' ns') if 'duration_ns' in e else 'Link Command',raw=e))
        facts=[f"Channel {channel} 自 Packet {anchor['index']}（{seconds(anchor['timestamp_ns'])} s）起，觀察到「{title.split('，')[0]}」。",
               '這段可見尾端的 LFPS：'+', '.join(f'{name} × {count}' for name,count in sorted(names.items()))+'。',
               '同 channel 此後的保存資料未再見 LGOOD／LCRD；這只表示 Link Command 未見，不代表已證明 Link 或裝置故障。']
        gaps=['capture 起訖與資料連續性未知；先排除擷取在這裡截斷或顯示過濾。',
              '未取得精確 LTSSM state、USB3 payload／Transfer 結果；不能推算狀態或根因。']
        if prior:facts.append(f"同 channel 前一筆可見 Link Command 是 Packet {prior['index']}（{seconds(prior['timestamp_ns'])} s，{prior['name']}）。")
        else:gaps.append('此 channel 沒有前置 LGOOD／LCRD 參考，可能從流程中途開始擷取。')
        candidates.append(dict(title=title,start_ns=anchor['timestamp_ns'],end_ns=relevant[-1]['timestamp_ns'],
              native_targets=[target('USB3',0,anchor['index'],anchor['timestamp_ns'],channel)],facts=facts,
              reasons=['同一 channel 的多個事件形成連續調查線索；合併同段重複事件，避免讓每筆 Polling 佔一個候選。'],
              next_step=f"先在 PKT 展開 Packet {anchor['index']}，核對 channel {channel} 的 {anchor['name']} 與同段 Polling／Reset 記錄；再向後找 LGOOD／LCRD。若已有後續 Link 流量，先確認擷取／過濾範圍，再對照資料傳輸；若剛好到 capture 結尾，先補後段，不先判韌體故障。",
              evidence_gaps=gaps,context=context,evidence_completeness='partial',
              _priority=0 if bad and resets else 1 if wake_reset else 2 if resets else 3))
    candidates.sort(key=lambda c:(c['_priority'],c['start_ns']))
    for c in candidates:c.pop('_priority')
    analysis.update(episode_count=len(candidates),candidates=candidates[:3])
    return analysis


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=normalize(json.loads(a.input.read_text(encoding='utf-8-sig')))
    with a.output.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False)
