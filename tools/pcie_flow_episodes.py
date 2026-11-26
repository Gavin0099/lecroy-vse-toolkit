"""Directional observation intervals, not inferred physical-device episodes."""
import copy
from collections import OrderedDict
import pcie_stage_summary as stages

IDENTITY=('source_trace_sha256','display_trace_sha256','packet_namespace')

def build(summary):
    groups=OrderedDict()
    def group(a):
        key=(a.get('channel'),a.get('direction'),a.get('epoch'))
        if key not in groups:
            groups[key]=dict(scenario_id='ch-'+str(key[0])+'-'+str(key[1])+'-epoch-'+str(key[2]),
                link_scope=dict(channel=key[0],direction=key[1],epoch=key[2],physical_link_id='UNKNOWN'),milestones=[],events=[])
        return groups[key]
    for row in summary['events']:
        if any(row.get(k)!=summary[k] for k in IDENTITY):raise ValueError('Flow event belongs to another capture')
        group(row)['events'].append(copy.deepcopy(row))
    for m in summary['observed_milestones']:
        if any(m['anchor'].get(k)!=summary[k] for k in IDENTITY):raise ValueError('Flow milestone belongs to another capture')
        group(m['anchor'])['milestones'].append(copy.deepcopy(m))
    episodes=[]
    for g in groups.values():
        structural=[r for r in g['events'] if r['kind'] in ('LTSSM','LINK')]
        anchors=[stages.anchor(r) for r in structural]+[m['anchor'] for m in g['milestones']]
        if not anchors:continue  # PM/NAK by themselves are background, not a review target.
        anchors.sort(key=lambda a:a['packet_index'])
        latest=structural[-1] if structural else None
        usable_l0=latest is not None and latest['kind']=='LTSSM' and latest.get('valid')==1 and latest.get('state_name')=='L0' and latest['direction']!='UNKNOWN'
        has_down=any(m['kind']=='LINK_DOWN_OBSERVED' for m in g['milestones'])
        has_train=any(m['kind']=='TRAINING_OBSERVED' for m in g['milestones'])
        g.update(start_packet=anchors[0]['packet_index'],end_packet=anchors[-1]['packet_index'],
            observed_kind='LINK_DISCONNECT_RETRAIN' if has_down and has_train else 'LINK_TRANSITION' if has_down else 'LINK_TRAINING' if has_train else 'CONFIG_TRAFFIC' if any(m['kind']=='CONFIG_REQUEST_OBSERVED' for m in g['milestones']) else 'L0_OBSERVATION' if usable_l0 else 'UNKNOWN',
            last_supported_milestone=g['milestones'][-1] if g['milestones'] else None,
            current_l0=stages.anchor(latest) if usable_l0 else None,
            focus_anchor=stages.anchor(latest) if latest else anchors[-1],
            expected_context=None,observations=[dict(kind=m['kind'],output_class='OBSERVED',anchor=m['anchor'],explanation=m['explanation']) for m in g['milestones']],
            evidence_refs=list({str(a['evidence_ref']):a['evidence_ref'] for a in anchors if a.get('evidence_ref')}.values()))
        episodes.append(g)
    return sorted(episodes,key=lambda e:(e['start_packet'],e['scenario_id']))

def validate_context(value,model):
    if value is None:return None
    allowed={'kind','description','source','scope',*IDENTITY}
    if not isinstance(value,dict) or set(value)!=allowed:raise ValueError('Unsupported engineering context fields')
    if value['kind'] not in ('EXPECTED_HOTPLUG','UNEXPECTED_LINK_DOWN'):raise ValueError('Unsupported context kind')
    if any(value[k]!=model[k] for k in IDENTITY):raise ValueError('Engineering context belongs to another trace')
    if any(not isinstance(value[k],str) or not value[k].strip() or len(value[k])>1200 for k in ('description','source')):raise ValueError('Context requires description and source')
    scope=value['scope']
    if scope is not None:
        if not isinstance(scope,dict) or set(scope)!={'channel','direction','epoch','start_packet','end_packet'}:raise ValueError('Invalid context scope')
        if any(type(scope[k]) is not int or scope[k]<0 for k in ('channel','epoch','start_packet','end_packet')) or scope['direction'] not in ('Upstream','Downstream'):raise ValueError('Context scope must be explicit')
        if scope['start_packet']>scope['end_packet']:raise ValueError('Reversed context range')
        bound=model['coverage'].get('native_packet_count')
        if bound is None or scope['end_packet']>=bound:raise ValueError('Context outside verified packet range')
    return copy.deepcopy(value)

def overlay(episodes,context):
    result=copy.deepcopy(episodes)
    for e in result:
        e['context_binding']='NOT_PROVIDED' if context is None else 'BACKGROUND_ONLY' if context['scope'] is None else 'OUTSIDE_SCOPE'
        for o in e['observations']:
            a=o['anchor'];s=context['scope'] if context else None
            matches=s and all(a.get(k)==s[k] for k in ('channel','direction','epoch')) and s['start_packet']<=a['packet_index']<=s['end_packet']
            if matches and o['kind']=='LINK_DOWN_OBSERVED':
                e['context_binding']='SCOPED_ENGINEER_INPUT';e['expected_context']=copy.deepcopy(context)
                o.update(output_class='EXPECTED_CONTEXT' if context['kind']=='EXPECTED_HOTPLUG' else 'CHECK_RECOMMENDED',
                    interpretation='在工程師指定區間內的預期切換；後續恢復與初始化仍需核對。' if context['kind']=='EXPECTED_HOTPLUG' else '工程師指出此區間不預期斷線；請核對操作 marker 與重新訓練。')
    return result
