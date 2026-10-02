import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2c_capability_resolution as b2c
import b2b_config_access as b2b
ROOT=Path(__file__).resolve().parents[2]
REF=json.loads((ROOT/'docs/pcie-register-reference.json').read_text())


def fixture():
    # PCIe at 0x60 and PM at 0xA0; intentionally different from the real capture.
    reads=[(0xC,0),(0x34,0x60),(0x60,0x0002A010),(0xA0,1),(0x100,0x1801001E)]
    rows=[]
    for i,(offset,value) in enumerate(reads):
        rows.append(dict(device_id=256,epoch='before_disconnect',read_value=value,write_value=None,first_be=15,register_byte_offset=offset,packet_index=10+2*i,completions=[{'packet_index':11+2*i}],access_id=f'fixture-{i}'))
    return dict(schema=b2b.SCHEMA,anchors=dict(disconnect_packet=100,reconnect_packet=200),accesses=rows)


class CapabilityTests(unittest.TestCase):
    def test_conventional_relative_registers_stay_below_0x100(self):
        for base,cap in ((0xFC,16),(0xFC,1),(0xEC,16)):
            log=fixture();log['accesses'][1]['read_value']=base
            log['accesses'][2].update(register_byte_offset=base,read_value=cap)
            d=b2c.resolve(log,REF,256,99)
            if base==0xEC:
                self.assertEqual(d['registers']['LinkControl']['byte_offset'],0xFC)
                self.assertEqual(d['registers']['LinkStatus']['byte_offset'],0xFE)
            elif cap==16:
                self.assertNotIn('LinkControl',d['registers'])
                self.assertNotIn('LinkStatus',d['registers'])
                self.assertIn('OUT_OF_RANGE_LinkControl',d['gaps'])
            else:
                self.assertNotIn('PMCSR',d['registers'])

    def test_extended_whole_register_span_cannot_cross_0x1000(self):
        log=fixture();log['accesses'][4]['read_value']=0xFF410001
        log['accesses'].append({**log['accesses'][4],'packet_index':30,'completions':[{'packet_index':31}],
                                'register_byte_offset':0xFF4,'read_value':0x1001E})
        d=b2c.resolve(log,REF,256,99)
        self.assertEqual(d['registers']['L1SSControl1']['byte_offset'],0xFFC)
        self.assertNotIn('L1SSControl2',d['registers'])
        # Modified reference tests the span guard; it is not a qualified layout.
        ref=copy.deepcopy(REF);ref['relative_offsets']['L1SSControl2']=11
        d=b2c.resolve(log,ref,256,99)
        self.assertNotIn('L1SSControl2',d['registers'])
        self.assertIn('OUT_OF_RANGE_L1SSControl2',d['gaps'])

    def test_relative_offsets_and_incomplete_ext_chain(self):
        d=b2c.resolve(fixture(),REF,256,99)
        self.assertEqual(d['registers']['LinkControl']['byte_offset'],0x70)
        self.assertEqual(d['registers']['PMCSR']['byte_offset'],0xA4)
        self.assertEqual(d['registers']['L1SSControl1']['byte_offset'],0x108)
        self.assertTrue(d['conventional_chain']['complete'])
        self.assertEqual(d['extended_chain']['gap'],'HEADER_NOT_OBSERVED_0x180')

    def test_no_future_completion_or_new_epoch_leak(self):
        log=fixture();d=b2c.resolve(log,REF,256,14)
        self.assertNotIn('LinkControl',d['registers'])
        d=b2c.resolve(log,REF,256,15);self.assertIn('LinkControl',d['registers'])
        for packet in (150,250):
            d=b2c.resolve(log,REF,256,packet);self.assertNotIn('LinkControl',d['registers']);self.assertIsNone(d['header_type'])

    def test_missing_node_cycle_invalid_pointer_and_duplicate_id(self):
        log=fixture();log['accesses'][2]['read_value']=0x62<<8|0x10
        self.assertIn('INVALID_POINTER',b2c.resolve(log,REF,256,99)['conventional_chain']['gap'])
        log=fixture();log['accesses'][3]['read_value']=0x60<<8|1
        self.assertIn('CYCLE',b2c.resolve(log,REF,256,99)['conventional_chain']['gap'])
        log=fixture();del log['accesses'][3]
        self.assertEqual(b2c.resolve(log,REF,256,99)['conventional_chain']['gap'],'HEADER_NOT_OBSERVED_0xA0')
        log=fixture();log['accesses'][3]['read_value']=16
        d=b2c.resolve(log,REF,256,99);self.assertNotIn('LinkControl',d['registers']);self.assertIn('DUPLICATE_PCIe',d['gaps'])

    def test_header_unknown_and_other_bdf_no_map(self):
        log=fixture();log['accesses']=log['accesses'][1:]
        d=b2c.resolve(log,REF,256,99);self.assertNotIn('BAR0',d['registers']);self.assertNotIn('LinkControl',d['registers'])
        d=b2c.resolve(fixture(),REF,512,99);self.assertNotIn('LinkControl',d['registers'])

    def test_real_chain(self):
        p=ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        d=b2c.resolve(json.loads(p.read_text()),REF,256,225040)
        self.assertEqual([n['byte_offset'] for n in d['conventional_chain']['nodes']],[0x80,0xE0,0xF8])
        self.assertTrue(d['conventional_chain']['complete'])
        self.assertEqual(d['registers']['LinkControl']['byte_offset'],0x90)
        self.assertEqual(d['registers']['PMCSR']['byte_offset'],0xFC)
        self.assertEqual(d['registers']['L1SSControl1']['byte_offset'],0x118)
        self.assertEqual(d['extended_chain']['gap'],'HEADER_NOT_OBSERVED_0x200')


if __name__=='__main__':unittest.main()
