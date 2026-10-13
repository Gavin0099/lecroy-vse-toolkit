"""Independent LC-04/USB-01 widths, count and unknown-state fixture expectations."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "tools"))
import usb_field_probe as f
import s01_contract as s


class FieldTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.plan=f.prepare(Path(self.tmp.name)/"plan","U02","a"*64,2)

    def result(self):
        # LC-04 PDF32 field roles; USB-01 7.2.2.2 independently gives 11/5-bit widths.
        return {"slice":"U02","trace_sha256":"a"*64,"script_sha256":self.plan["script_sha256"],
            "integrity":{"source_unchanged":True,"working_copy_unchanged":True,"working_copy_readonly":True},
            "run_result":2,"finished_result":2,"error":"","summary":[3,3,2,0,0],
            "reports":["native header", "U02|10|1|2|5|4|0|0|0|0|0|LGOOD_0|SS",
                       "U02|11|1|3|6|5|9|2047|31|2047|31|LCRD1_A|SSP", "U02-UNSUPPORTED-MODE|0"]}

    def test_handwritten_rows_boundaries_and_packet_references(self):
        r=self.result(); original=copy.deepcopy(r); a=f.assess(r,self.plan)
        self.assertEqual(a["exported_count"],2); self.assertTrue(a["sample_truncated"])
        self.assertEqual(a["records"][1]["replica_crc5_raw"],31)
        self.assertEqual(a["records"][1]["mode_observed"],"SSP")
        self.assertEqual(a["records"][0]["packet_ref"],{"trace_sha256":"a"*64,"index":10,"level":"_PKT","channel_raw":5})
        self.assertEqual(a["crc_correctness"],"NOT_EVALUATED"); self.assertEqual(r,original)

    def test_unknown_name_remains_raw_and_is_not_unsupported(self):
        r=self.result(); r["reports"][1]="U02|10|1|2|5|4|999|0|0|0|0|UNK(999)|SS"
        row=f.assess(r,self.plan)["records"][0]
        self.assertEqual(row["lnkcmd_raw"],999); self.assertEqual(row["name_state"],"unknown")

    def test_missing_truncated_or_duplicate_rows_fail_closed(self):
        for mutation in [lambda r:r["reports"].pop(1),lambda r:r["reports"].append(r["reports"][1]),lambda r:r["reports"].__setitem__(1,r["reports"][1][:-3])]:
            r=self.result(); mutation(r)
            with self.assertRaises(s.ContractError):f.assess(r,self.plan)

    def test_doc_widths_and_timestamp_boundaries_are_independent(self):
        for line in ["U02|10|1|2|5|4|0|2048|0|0|0|LGOOD_0|SS", "U02|10|1|2|5|4|0|0|32|0|0|LGOOD_0|SS",
                     "U02|10|1|1000000000|5|4|0|0|0|0|0|LGOOD_0|SS", "U02|10|1|2|5|4|0|0|0|2048|0|LGOOD_0|SS"]:
            r=self.result();r["reports"][1]=line
            with self.assertRaises(s.ContractError):f.assess(r,self.plan)

    def test_unknown_mode_does_not_get_guessed_fields(self):
        r=self.result();r["summary"]=[4,3,2,0,0];r["reports"][-1]="U02-UNSUPPORTED-MODE|1"
        self.assertEqual(f.assess(r,self.plan)["unsupported_mode_count"],1)
        r["reports"][1]="U02|10|1|2|5|4|0|0|0|0|0|LGOOD_0|UNKNOWN"
        with self.assertRaises(s.ContractError):f.assess(r,self.plan)

    def test_zero_sample_is_unknown_not_protocol_pass(self):
        r=self.result();r["summary"]=[0,0,0,0,0];r["reports"]=["U02-UNSUPPORTED-MODE|0"]
        a=f.assess(r,self.plan);self.assertEqual(a["records"],[])
        self.assertEqual(a["qualification"],"NOT_EVALUATED")

    def test_wrong_binding_integrity_finished_marker_and_hidden_verdict_rejected(self):
        for key,value in [("trace_sha256","b"*64),("script_sha256","b"*64),("finished_result",True),("error","failure"),("summary",None),("verdict","PASS")]:
            r=self.result();r[key]=value
            with self.assertRaises(s.ContractError):f.assess(r,self.plan)
        r=self.result();r["integrity"]["source_unchanged"]=False
        with self.assertRaises(s.ContractError):f.assess(r,self.plan)

    def test_changed_plan_and_existing_output_rejected(self):
        p=copy.deepcopy(self.plan);p["script"]="../../anything.vse"
        with self.assertRaises(s.ContractError):f.validate_plan(p)
        with self.assertRaises(FileExistsError):f.prepare(Path(self.tmp.name)/"plan","U02","a"*64)

    def test_manifest_keeps_capture_mode_epoch_and_retention_unknown(self):
        before={"source":{"sha256":"a"*64},"toolchain":{"software_version":"synthetic-only","constants":{"sha256":"b"*64}}}
        m=f.manifest(self.result(),self.plan,before,"fixture://result","c"*64,"fixture://before","d"*64)
        self.assertEqual(s.validate_manifest(m),[])
        self.assertEqual(m["trace"]["facts"]["mode"]["state"],"unknown")
        self.assertEqual(m["trace"]["facts"]["epoch"]["value"],None)
        self.assertEqual(m["observations"][0]["coverage"]["retention"],"unknown")
        self.assertEqual(m["observations"][0]["count"],2)
        self.assertEqual(m["capabilities"][0]["availability"],"available")

    def test_missing_toolchain_metadata_cannot_create_a_supported_manifest(self):
        for before in [None,{}, {"source":{"sha256":"a"*64},"toolchain":{}},
                       {"source":{"sha256":"a"*64},"toolchain":{"software_version":"v","constants":{"sha256":"not-a-hash"}}}]:
            with self.assertRaises(s.ContractError):f.manifest(self.result(),self.plan,before,"fixture://result","c"*64,"fixture://before","d"*64)


class LfpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.plan=f.prepare(Path(self.tmp.name)/"plan","U03","a"*64,2)

    def result(self):
        return {"slice":"U03","trace_sha256":"a"*64,"script_sha256":self.plan["script_sha256"],
            "integrity":{"source_unchanged":True,"working_copy_unchanged":True,"working_copy_readonly":True},
            "run_result":2,"finished_result":2,"error":"","summary":[1,1,1,0,0],
            "reports":["U03|12|1|2|5|4|65|1000|0|1000|0|1|LFPS_POLLING|SS", "U03-UNSUPPORTED-MODE|0"]}

    def test_raw_name_units_pattern_flag_and_unknown_resolution_preserved(self):
        r=f.assess(self.result(),self.plan)["records"][0]
        self.assertEqual((r["type_raw"],r["duration_raw_ns"],r["duration_remainder_ns"],r["starts_pattern"]),(65,1000,1000,1))
        self.assertEqual(r["name_vendor"],"LFPS_POLLING")
        self.assertEqual(r["measurement_resolution"],"unknown")
        self.assertEqual(r["wake_reset_success"],"NOT_EVALUATED")

    def test_unknown_type_is_not_guessed_from_duration(self):
        r=self.result();r["reports"][0]="U03|12|1|2|5|4|999|1000|0|1000|0|1|UNK(999)|SS"
        record=f.assess(r,self.plan)["records"][0]
        self.assertEqual(record["type_raw"],999);self.assertEqual(record["name_state"],"unknown")

    def test_missing_negative_duration_bad_flag_and_remainder_are_rejected(self):
        for line in ["U03|12|1|2|5|4|65|-1|0|1000|0|1|LFPS_POLLING|SS",
                     "U03|12|1|2|5|4|65|1000|0|1000|0|2|LFPS_POLLING|SS",
                     "U03|12|1|2|5|4|65|1000|0|1000000000|0|1|LFPS_POLLING|SS"]:
            r=self.result();r["reports"][0]=line
            with self.assertRaises(s.ContractError):f.assess(r,self.plan)

    def test_empty_sample_does_not_establish_pattern_or_wake_success(self):
        r=self.result();r["reports"]=["U03-UNSUPPORTED-MODE|0"];r["summary"]=[0,0,0,0,0]
        a=f.assess(r,self.plan);self.assertEqual(a["records"],[]);self.assertEqual(a["qualification"],"NOT_EVALUATED")


if __name__=="__main__":unittest.main()
