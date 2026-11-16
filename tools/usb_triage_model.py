"""Product presentation and native targets; protocol analysis stays separate."""
from __future__ import annotations
import copy
import html

FORMAT = 'usb-triage-inspection/v1'
PROTOCOLS = ('USB2', 'USB3', 'PD')
STATES = {'analyzed', 'not_observed', 'partial', 'unsupported', 'failed'}
LABELS = {0: 'Packet', 1: 'Transaction', 3: 'Transfer'}
STATE_TEXT = {'analyzed': '已分析', 'not_observed': '未觀察到', 'partial': '資料部分缺漏',
              'unsupported': '尚未支援', 'failed': '執行失敗'}


def target(protocol, level, index, timestamp_ns=None, channel=None):
    value = dict(protocol=protocol, level=level, index=index, timestamp_ns=timestamp_ns, channel=channel)
    validate_target(value)
    return value


def validate_target(t):
    if not isinstance(t, dict) or set(t) - {'protocol', 'level', 'index', 'timestamp_ns', 'channel'}:
        raise ValueError('Invalid native target fields')
    if t.get('protocol') not in PROTOCOLS or type(t.get('level')) is not int:
        raise ValueError('Invalid native protocol/level')
    if t['level'] not in ({3} if t['protocol'] == 'USB2' else {0} if t['protocol'] == 'USB3' else {0, 1, 3}):
        raise ValueError('Unsupported native level for protocol')
    if type(t.get('index')) is not int or not 0 <= t['index'] <= 2147483647:
        raise ValueError('Invalid native unit index')
    for name in ('timestamp_ns', 'channel'):
        if t.get(name) is not None and (type(t[name]) is not int or not 0 <= t[name] <= 9223372036854775807):
            raise ValueError('Invalid native target ' + name)
    return t


def targets(card):
    if 'native_targets' in card:
        return card['native_targets']
    return [target('USB2', 3, card['transfer_indices'][0], card.get('start_ns'))]


def location(t):
    return f"{t['protocol']} · {LABELS[t['level']]} {t['index']}"


def seconds(ns):
    return f'{ns // 1000000000}.{ns % 1000000000:09d}'


def validate(model):
    if model.get('format') != FORMAT:
        raise ValueError('Unsupported inspection format')
    digest = model.get('trace_sha256', '')
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid trace identity')
    analyses = model.get('analyses')
    if not isinstance(analyses, list) or any(not isinstance(a,dict) for a in analyses) or {a.get('protocol') for a in analyses} != set(PROTOCOLS) or len(analyses) != 3:
        raise ValueError('Invalid protocol analyses')
    for a in analyses:
        if a.get('state') not in STATES or not isinstance(a.get('coverage'), dict):
            raise ValueError('Invalid protocol analysis status')
    cards = model.get('candidates')
    if not isinstance(cards, list) or len(cards) > 9:
        raise ValueError('Invalid candidates')
    counts = dict.fromkeys(PROTOCOLS, 0)
    for rank, c in enumerate(cards, 1):
        if not isinstance(c,dict) or type(c.get('rank')) is not int or c.get('rank') != rank or c.get('protocol') not in PROTOCOLS:
            raise ValueError('Invalid candidate identity')
        counts[c['protocol']] += 1
        if counts[c['protocol']] > 3 or type(c.get('protocol_rank')) is not int or c.get('protocol_rank') != counts[c['protocol']]:
            raise ValueError('Invalid protocol candidate rank')
        ts = c.get('native_targets')
        if not isinstance(ts, list) or not 1 <= len(ts) <= 16:
            raise ValueError('Invalid candidate native targets')
        for t in ts:
            validate_target(t)
            if t['protocol'] != c['protocol']:
                raise ValueError('Native protocol does not match candidate')
        if type(c.get('start_ns')) is not int or type(c.get('end_ns')) is not int or not 0 <= c['start_ns'] <= c['end_ns']:
            raise ValueError('Invalid candidate interval')
    for a in analyses:
        n = a.get('episode_count')
        if type(n) is not int or n < counts[a['protocol']]:
            raise ValueError('Invalid candidate total')
        if a['state'] in ('not_observed', 'unsupported', 'failed') and counts[a['protocol']]:
            raise ValueError('Candidate without supported analysis')
    observations=model.get('observations',[])
    if not isinstance(observations,list) or len(observations)>24:raise ValueError('Invalid observed flows')
    for rank,c in enumerate(observations,1):
        if not isinstance(c,dict) or c.get('kind')!='observation' or c.get('protocol')!='PD' or type(c.get('rank')) is not int or c['rank']!=rank:
            raise ValueError('Invalid observed flow identity')
        ts=c.get('native_targets')
        if not isinstance(ts,list) or not 1<=len(ts)<=16:raise ValueError('Invalid observed flow targets')
        for t in ts:
            validate_target(t)
            if t['protocol']!='PD':raise ValueError('Observed flow protocol mismatch')
        if type(c.get('start_ns')) is not int or type(c.get('end_ns')) is not int or not 0<=c['start_ns']<=c['end_ns']:raise ValueError('Invalid observed flow interval')
    pd=next(a for a in analyses if a['protocol']=='PD')
    if observations and (pd['state'] not in ('analyzed','partial') or type(pd.get('observation_count')) is not int or pd['observation_count']<len(observations)):
        raise ValueError('Observed flows without supported data')
    return model


def compose(digest, analyses):
    """Accept protocol-local results, preserving per-protocol priority only."""
    cards, summaries, observations = [], [], []
    for protocol in PROTOCOLS:
        analysis = copy.deepcopy(next(a for a in analyses if a['protocol'] == protocol))
        local = analysis.pop('candidates', [])
        for card in analysis.pop('observations',[]):
            card.update(rank=len(observations)+1,protocol=protocol,kind='observation')
            observations.append(card)
        for rank, card in enumerate(local[:3], 1):
            card.update(rank=len(cards) + 1, protocol=protocol, protocol_rank=rank)
            cards.append(card)
        analysis.setdefault('episode_count', len(local))
        summaries.append(analysis)
    return validate(dict(format=FORMAT, trace_sha256=digest, rule_version='usb-multiprotocol/1',
                         status='candidates_found' if cards else 'no_supported_candidate',
                         scope='USB2 EP0 / USB3 Link・LFPS / PD 協商・VDM；無候選不代表 USB PASS。',
                         candidates=cards, observations=observations, analyses=summaries,
                         episode_count=sum(a['episode_count'] for a in summaries),
                         omitted_episodes=sum(a['episode_count'] for a in summaries)-len(cards),
                         limitations=['各協定獨立排序；時間接近不代表因果。',
                                      '未涵蓋完整 USB3 bulk/streams、精確 LTSSM state、完整 PD 延伸訊息或合規判定。']))


def render(model):
    validate(model)
    esc = lambda x: html.escape(str(x))
    def lines(values):
        return '<ul>' + ''.join('<li>' + esc(x) + '</li>' for x in values) + '</ul>'
    body = '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>USB Trace Triage</title>'
    body += '<style>body{font:16px system-ui,"Microsoft JhengHei";background:#f5f5f5;color:#242424;margin:24px}main{max-width:1100px;margin:auto}section,article{background:white;padding:20px;margin:16px 0}h2{font-size:22px}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #ddd}summary{cursor:pointer}code{white-space:pre-wrap;overflow-wrap:anywhere}:focus-visible{outline:2px solid #0f6cbd;outline-offset:3px}</style><main><header><h1>優先檢查工作區</h1>'
    body += '<p>' + esc(model['scope']) + '</p><p>SHA-256 ' + esc(model['trace_sha256']) + '</p></header>'
    for a in model['analyses']:
        body += '<section><h2>' + esc(a['protocol']) + ' · ' + STATE_TEXT[a['state']] + '</h2>'
        body += '<p>' + esc(a.get('scope', '')) + '；找到 ' + str(a['episode_count']) + ' 個區段。</p>'
        body += lines(a.get('limitations', []))
        cs = [c for c in model['candidates'] if c['protocol'] == a['protocol']]
        if not cs:
            body += '<p>本範圍未提供候選。請依上方資料狀態判讀，不能當成 USB PASS。</p>'
        flows=[c for c in model.get('observations',[]) if c['protocol']==a['protocol']]
        if flows:body+='<p>另有 '+str(a['observation_count'])+' 個已觀察流程；以下最多顯示 24 個，均未列為可疑候選。</p>'
        for c in cs+flows:
            observed=c.get('kind')=='observation'
            body += f'<article class="card" id="'+('observation-' if observed else 'candidate-')+str(c['rank'])+'"><h2>'+('已觀察流程 · ' if observed else '#'+str(c['protocol_rank'])+' ')+esc(c['title'])+'</h2>'
            body += '<p>' + esc(location(c['native_targets'][0])) + ' · ' + seconds(c['start_ns']) + ' s</p>'
            body += '<h3>工程師下一步</h3><p>' + esc(c['next_step']) + '</p><h3>發生什麼事</h3>' + lines(c['facts'])
            body += '<h3>為什麼先看這裡</h3>' + lines(c['reasons'])
            body += '<details><summary>前後事件與限制</summary>' + lines(c.get('evidence_gaps', []))
            body += '<code>' + esc(__import__('json').dumps(c.get('context', []), ensure_ascii=False, indent=2)) + '</code></details></article>'
        body += '</section>'
    return body + lines(model['limitations']) + '</main></html>'
