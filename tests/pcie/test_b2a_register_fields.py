import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/pcie"))
import b2a_register_fields as b2a

# Reviewed literal packet samples: byte order and mask expectations are independent
# of the verifier's field slicing. Includes a zero-valued field and absent read data.
READ = 'B2A_ROW|3148|8.277 sec|Downstream|0x9|0x0|0x4|0x100|0xF8|NA|NA|0xF|0x0|0x0|NA|NA|NA|NA|NA|FB05D4040000010000040F010000F8EA'
RETURN = 'B2A_ROW|3150|8.277 sec|Upstream|0x12|0x0|0x4|NA|NA|0x0|0xF7C30001|NA|NA|0x4|0100C3F7|0x100|0x0|0x4|0x0|FB057E4A000001010000040000040001'
WRITE = 'B2A_ROW|3312|8.277 sec|Downstream|0xA|0x0|0x6|0x100|0xFC|NA|0x800B|0x3|0x0|0x4|0B800000|NA|NA|NA|NA|FB05E94400000100000603010000FC0B'


def fixture():
    rows, end = b2a.parse(b2a.HEADER+'\n' + '\n'.join((READ, RETURN, WRITE)) + '\nB2A_END|tlps=3|rows=3|reason=trace_end')
    meta = [dict(row=i+1, tlp_type_hex=hex(r['tlp_type']), **{k:r[k] for k in ('packet_index','time_display','channel','requester_id','tag','completer_id','compl_status')}) for i,r in enumerate(rows)]
    return rows, end, meta


class ProbeTests(unittest.TestCase):
    def test_full_raw_dword_independent_of_decoder_fields(self):
        rows,end,meta=fixture()
        # Synthetic no-payload padding; literal DWORD continuations independent of fields.
        rows[0]['frame_prefix']+='000000'
        rows[1]['frame_prefix']+='00C3F7'
        rows[2]['frame_prefix']+='800000'
        self.assertEqual(b2a.verify(rows,end,meta,require_full_payload=True)['payload_dwords_checked'],2)
        rows[1]['payload_prefix']='0100C3F6'
        rows[1]['register_data']=0xF6C30001
        with self.assertRaisesRegex(ValueError,'Frame/payload'):
            b2a.verify(rows,end,meta,require_full_payload=True)

    def test_historical_prefix_cannot_qualify_full_dword(self):
        rows,end,meta=fixture()
        with self.assertRaisesRegex(ValueError,'Full raw'):
            b2a.verify(rows,end,meta,require_full_payload=True)

    def test_decoder_length_cannot_shrink_raw_data_dword(self):
        for length,prefix in ((0,None),(1,'01')):
            rows,end,meta=fixture()
            rows[1]['frame_prefix']+='00C3F7'
            rows[2]['frame_prefix']+='800000'
            rows[1].update(payload_length=length,payload_prefix=prefix,register_data=0x12345678)
            with self.subTest(length=length), self.assertRaisesRegex(ValueError,'Raw header/payload length'):
                b2a.verify(rows,end,meta,require_full_payload=True)

    def test_missing_cpld_register_data_is_explicit_unknown_not_dword_proof(self):
        rows,end,meta=fixture()
        rows[1]['frame_prefix']+='00C3F7'
        rows[2]['frame_prefix']+='800000'
        rows[1]['register_data']=None
        counts=b2a.verify(rows,end,meta,require_full_payload=True)
        self.assertEqual(counts['raw_payload_dwords_checked'],2)
        self.assertEqual(counts['payload_dwords_checked'],1)
        self.assertEqual(counts['register_data_payloads_unknown'],1)
        self.assertIsNone(rows[1]['register_data'])

    def test_fresh_raw_evidence_and_legacy_cli_gate(self):
        root=Path(__file__).resolve().parents[2]
        metadata=root/'artifacts/evidence/pcie-p4a-hang-20260914/g2a/export/fields.json'
        rows,end=b2a.parse((root/'artifacts/evidence/pcie-b2a-raw-dword-20261002/com-run1/vse-output.txt').read_text())
        counts=b2a.verify(rows,end,json.loads(metadata.read_text()),require_full_payload=True)
        self.assertEqual(counts['payload_dwords_checked'],59)
        self.assertEqual(counts['raw_payload_dwords_checked'],270)
        self.assertEqual(counts['register_data_payloads_unknown'],211)
        self.assertEqual(bytes.fromhex(next(r['frame_prefix'] for r in rows if r['packet_index']==3150))[15:19],bytes.fromhex('0100C3F7'))
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)/'out'
            self.assertEqual(b2a.main(['--com-run',str(root/'artifacts/evidence/pcie-b2a-hang-20260930/com-run1'),
                                      '--metadata',str(metadata),'--output-dir',str(dest)]),2)
            self.assertFalse(dest.exists())

    def test_literal_sample_bytes_and_masks(self):
        rows,end,meta=fixture()
        self.assertEqual(b2a.verify(rows,end,meta),dict(config_reads=1,config_writes=1,completions=1,payload_dwords_checked=2))
        self.assertIsNone(rows[0]['register_data']); self.assertEqual(rows[2]['first_be'],3)
        self.assertEqual(rows[1]['lower_addr'],0)

    def test_offset_index_and_mask_mismatch_rejected(self):
        for field,value in (('register',0x3E),('first_be',3),('device_id',0)):
            rows,end,meta=fixture();rows[0][field]=value
            with self.assertRaises(ValueError): b2a.verify(rows,end,meta)

    def test_endian_and_frame_payload_mismatch(self):
        for field,value in (('register_data',0x0100C3F7),('payload_prefix','0000C3F7'),('payload_length',8)):
            rows,end,meta=fixture();rows[1][field]=value
            with self.assertRaises(ValueError): b2a.verify(rows,end,meta)

    def test_read_request_must_not_be_returned_value(self):
        rows,end,meta=fixture();rows[0]['register_data']=0
        with self.assertRaises(ValueError):b2a.verify(rows,end,meta)

    def test_missing_end_duplicate_order_and_bad_numeric(self):
        for text in (b2a.HEADER+'\n'+READ, b2a.HEADER+'\n'+READ+'\n'+READ+'\nB2A_END|tlps=2|rows=2|reason=trace_end', b2a.HEADER+'\n'+READ.replace('0xF8','oops')+'\nB2A_END|tlps=1|rows=1|reason=trace_end', b2a.HEADER.replace('v1','v99')+'\n'+READ+'\nB2A_END|tlps=1|rows=1|reason=trace_end'):
            with self.assertRaises(ValueError):b2a.parse(text)

    def test_capture_metadata_and_unsupported_frame_rejected(self):
        rows,end,meta=fixture();meta[1]['tag']=9
        with self.assertRaises(ValueError):b2a.verify(rows,end,meta)
        rows,end,meta=fixture();rows[1]['frame_prefix']='00'+rows[1]['frame_prefix'][2:]
        with self.assertRaises(ValueError):b2a.verify(rows,end,meta)

    def test_real_run_fields(self):
        root=Path(__file__).resolve().parents[2]
        path=root/'artifacts/evidence/pcie-b2a-hang-20260930/com-run1/vse-output.txt'
        if not path.exists():self.skipTest('local trace evidence unavailable')
        rows,end=b2a.parse(path.read_text(encoding='utf-8'))
        meta=json.loads((root/'artifacts/evidence/pcie-p4a-hang-20260914/g2a/export/fields.json').read_text())
        self.assertEqual(b2a.verify(rows,end,meta)['config_reads'],32)
        self.assertEqual([r['register'] for r in rows if r['packet_index'] in (225043,225048)],[0x200,0x200])


if __name__=='__main__':unittest.main()
