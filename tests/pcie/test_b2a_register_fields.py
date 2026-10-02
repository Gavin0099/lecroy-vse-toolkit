import copy
import json
import sys
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
