"""Structural policy oracles; synthetic sequences are not hardware evidence."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb3_triage as u3


def event(index,name,channel=5):
    return dict(index=index,timestamp_ns=index*1000000,channel=channel,level=0,speed_raw=4,
                kind='LINK_CMD' if name.startswith(('LGOOD','LCRD')) else 'LFPS',name=name,duration_ns=100)


def data(events,partial=False):
    return dict(protocol='USB3',state='partial' if partial else 'analyzed',scope='fixture',trace_sha256='a'*64,
                coverage={'truncated':partial},limitations=[],events=events)


class GuidanceTests(unittest.TestCase):
    def test_compound_tail_is_one_candidate_at_first_wake_with_actionable_context(self):
        es=[event(1,'LGOOD_0'),event(2,'LFPS_WAKE_U3'),event(3,'LFPS_RESET')]+[event(n,'LFPS_POLLING') for n in range(4,30)]
        r=u3.discover(data(es));self.assertEqual(r['episode_count'],1)
        c=r['candidates'][0];self.assertEqual(c['native_targets'][0]['index'],2)
        self.assertEqual((c['start_ns'],c['end_ns']),(2000000,29000000))
        self.assertIn('capture',c['next_step']);self.assertIn('PKT',c['next_step'])
        self.assertTrue(c['facts'] and c['reasons'] and c['evidence_gaps'])
        self.assertIn(3,[e['index'] for e in c['context']]);self.assertLess(len(c['context']),15)
    def test_normal_wake_polling_single_reset_and_warning_do_not_create_candidate(self):
        for names in [['LFPS_WAKE_U3'],['LFPS_RESET'],['LFPS_ILLEGAL'],['LFPS_POLLING']*50,
                      ['LFPS_WAKE_U3','LFPS_RESET','LGOOD_0'],
                      ['LFPS_ILLEGAL','LFPS_RESET','LCRD_A']]:
            self.assertEqual(u3.discover(data([event(i+1,n) for i,n in enumerate(names)]))['candidates'],[])
    def test_channels_and_recovered_epochs_do_not_merge(self):
        es=[event(1,'LFPS_WAKE_U3',5),event(2,'LFPS_RESET',6)]
        self.assertEqual(u3.discover(data(es))['candidates'],[])
        es += [event(3,'LGOOD_0',5),event(4,'LFPS_RESET',5)]
        self.assertEqual(u3.discover(data(es))['candidates'],[])
    def test_two_channels_stay_two_regions_and_repeated_resets_aggregate(self):
        es=[event(1,'LFPS_RESET',5),event(2,'LFPS_RESET',5),event(3,'LFPS_RESET',5),
            event(4,'LFPS_ILLEGAL',6),event(5,'LFPS_RESET',6)]
        r=u3.discover(data(es));self.assertEqual(r['episode_count'],2)
        self.assertEqual({c['native_targets'][0]['channel'] for c in r['candidates']},{5,6})
    def test_partial_data_cannot_support_no_later_link_claim(self):
        r=u3.discover(data([event(1,'LFPS_WAKE_U3'),event(2,'LFPS_RESET')],True))
        self.assertEqual(r['candidates'],[]);self.assertIn('資料有截斷',r['limitations'][-1])
    def test_reset_or_illegal_with_polling_needs_prior_link_and_no_later_link(self):
        for trigger in ['LFPS_RESET','LFPS_ILLEGAL']:
            es=[event(1,'LGOOD_0'),event(2,trigger),event(3,'LFPS_POLLING')]
            self.assertEqual(u3.discover(data(es))['episode_count'],1)
            self.assertEqual(u3.discover(data(es[1:]))['candidates'],[])
            self.assertEqual(u3.discover(data(es+[event(4,'LGOOD_1')]))['candidates'],[])
        self.assertEqual(u3.discover(data([event(1,'LGOOD_0'),event(2,'LFPS_POLLING'),event(3,'LFPS_POLLING')]))['candidates'],[])
    def test_labels_and_time_translation_do_not_select_a_different_packet(self):
        a=data([event(1,'LFPS_WAKE_U3'),event(2,'LFPS_RESET')]);b=copy.deepcopy(a)
        b.update(filename='PASS_marker.usb',known_failure=999)
        for e in b['events']:e['timestamp_ns']+=10**12
        ca=u3.discover(a)['candidates'][0];cb=u3.discover(b)['candidates'][0]
        self.assertEqual(ca['native_targets'][0]['index'],cb['native_targets'][0]['index'])
        self.assertEqual(cb['start_ns']-ca['start_ns'],10**12)


if __name__=='__main__':unittest.main()
