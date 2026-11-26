"""Structural policies with independent native-shaped event fixtures.

No supplied failure labels/times, compliance timer or golden-root-cause oracle.
"""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import pd_triage as pd


def data(messages=(),outcomes=()):
    d=dict(protocol='PD',state='analyzed',scope='PD test',coverage={},limitations=[],packets=[],transactions=[],transfers=[])
    for i,m in enumerate(messages):
        sender=1 if m=='Request' else 2
        d['packets'].append(dict(index=i,timestamp_ns=i*1000,channel=9,sop_raw=1,sop='SOP',sender_port_raw=sender,packet_type_raw={'Request':34,'Accept':3,'PS Ready':6,'Reject':4,'Wait':12}.get(m,13)))
        d['transactions'].append(dict(level=1,index=i,timestamp_ns=i*1000,message=m,packet_anchor=i,sop='SOP',sop_raw=1,data_role='UFP' if sender==1 else 'DFP',power_role=None,status=None,cells=[]))
    for i,status in enumerate(outcomes):
        n=100+i
        d['packets'].append(dict(index=n,timestamp_ns=n*1000,channel=9,sop_raw=1,sop='SOP',sender_port_raw=2,packet_type_raw=47,vdm=dict(vendor='DisplayPort',command='DP Configure',command_type='REQ')))
        d['transfers'].append(dict(level=3,index=i,timestamp_ns=n*1000,message='DP Configure',vendor='DisplayPort',packet_anchor=n,sop='SOP',sop_raw=1,data_role=None,power_role='SRC',status=status,cells=[]))
    return d


class PDGuidanceTests(unittest.TestCase):
    def test_request_accept_restart_at_first_native_transaction(self):
        a=pd.discover(data(['Request','Accept','Request']))
        self.assertEqual(a['episode_count'],1)
        c=a['candidates'][0];self.assertEqual((c['native_targets'][0]['level'],c['native_targets'][0]['index']),(1,0))
        self.assertEqual(len(c['context']),3);self.assertTrue(c['next_step']);self.assertTrue(c['reasons'])
    def test_normal_completion_negative_response_and_capture_tail_not_faults(self):
        for seq in [['Request','Accept','PS Ready'],['Request','Reject'],['Request','Wait'],['Request','Accept'],['Request'],['Request','Accept','Request','Accept','PS Ready']]:
            self.assertEqual(pd.discover(data(seq))['candidates'],[],seq)
    def test_native_retry_not_recounted_and_single_nak_is_neutral(self):
        d=data(outcomes=['NAKed']);d['transfers'][0]['cells']=[('Retry Cnt','12'),('Cap Mismatch','1')]
        a=pd.discover(d);self.assertEqual(a['episode_count'],0);self.assertEqual(len(a['observations']),1)
        self.assertIn('Cap Mismatch',a['observations'][0]['reasons'][0])
    def test_repeated_vdm_aggregated_later_ack_recovers(self):
        a=pd.discover(data(outcomes=['NAKed','BUSY','NAKed']))
        self.assertEqual(a['episode_count'],1);self.assertEqual(len(a['candidates'][0]['context']),3)
        self.assertEqual(pd.discover(data(outcomes=['NAKed','NAKed','ACKed']))['candidates'],[])
    def test_sop_sender_channel_command_and_reset_boundaries(self):
        for key,value in [('sop_raw',2),('sender_port_raw',1),('channel',10)]:
            d=data(outcomes=['NAKed','NAKed']);d['packets'][-1][key]=value
            self.assertEqual(pd.discover(d)['candidates'],[],key)
        d=data(outcomes=['NAKed','NAKed']);d['packets'][-1]['vdm']['command']='Enter Mode'
        self.assertEqual(pd.discover(d)['candidates'],[])
        for t in [100500,102000]:
            d=data(outcomes=['NAKed','NAKed']);d['packets'].append(dict(index=300,timestamp_ns=t,channel=9,packet_type_raw=251));d['packets'].sort(key=lambda p:p['timestamp_ns'])
            self.assertEqual(pd.discover(d)['candidates'],[])
        d=data(['Request','Accept','Request']);d['packets'][1]['sender_port_raw']=1
        self.assertEqual(pd.discover(d)['candidates'],[])
    def test_partial_suppresses_absence_and_label_time_shift_invariant(self):
        d=data(['Request','Accept','Request']);d['filename']='PASS.usb'
        a=pd.discover(d);shift=9999999999
        for row in d['packets']+d['transactions']:row['timestamp_ns']+=shift
        d['filename']='FAIL.usb';b=pd.discover(d)
        self.assertEqual(a['episode_count'],b['episode_count']);self.assertEqual(b['candidates'][0]['start_ns']-a['candidates'][0]['start_ns'],shift)
        d['state']='partial';self.assertEqual(pd.discover(d)['candidates'],[])
    def test_matched_response_target_ignores_goodcrc_and_wrong_sender(self):
        d=data(outcomes=['NAKed']);p=copy.deepcopy(d['packets'][0]);p.update(index=160,timestamp_ns=101000,sender_port_raw=1);p['vdm']['command_type']='NAK';d['packets'].append(p)
        ts=pd.discover(d)['observations'][0]['native_targets'];self.assertEqual([t['index'] for t in ts],[0,100,160])
        p['sender_port_raw']=2;self.assertEqual(len(pd.discover(d)['observations'][0]['native_targets']),2)


if __name__=='__main__':unittest.main()
