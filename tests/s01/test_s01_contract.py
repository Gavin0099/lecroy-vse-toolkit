"""Independent S01 contract tests; expected states are handwritten fixtures.

These tests do not open traces, import pipelines, contact a service, or infer
protocol correctness. See fixture-oracles.md for requirement-level evidence.
"""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))
import s01_contract as contract


def fixture(name="complete-pcie.json"):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def profiles():
    return {row["slice_id"]: row for row in fixture("profiles.json")}


def unknown_fact():
    return {"state": "unknown", "value": None, "evidence_refs": []}


def one_profile(kind, identifier, expected, *, protocol="pcie", modes=None):
    return {
        "slice_id": "SYN-ONE-REQUIREMENT",
        "protocol": protocol,
        "modes": modes if modes is not None else ["non-Flit"],
        "engineer_question": "Does this metadata establish one named input prerequisite?",
        "expected_observation": "Input readiness only; qualification remains unevaluated.",
        "requirements": [{"kind": kind, "id": identifier, "expected": expected}],
    }


class ManifestTests(unittest.TestCase):
    def assert_invalid(self, doc):
        errors = contract.validate_manifest(doc)
        self.assertTrue(errors, "Contradictory or malformed metadata was accepted")
        for error in errors:
            self.assertIsInstance(error, dict)
            for key in ("code", "path", "message"):
                self.assertIsInstance(error.get(key), str, error)
                self.assertTrue(error[key], error)
        return errors

    def test_required_synthetic_cases_are_valid_unknown_is_not_malformed(self):
        for case in fixture("expected-readiness.json")["cases"]:
            with self.subTest(case=case["file"]):
                self.assertEqual(contract.validate_manifest(fixture(case["file"])), [])

    def test_manifest_validation_is_deterministic_and_does_not_mutate(self):
        doc = fixture()
        before = copy.deepcopy(doc)
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(doc, before)

    def test_missing_required_key_is_not_the_unknown_state(self):
        for key in ("mode", "epoch", "filters"):
            with self.subTest(key=key):
                doc = fixture()
                del doc["trace"]["facts"][key]
                self.assert_invalid(doc)

    def test_schema_version_is_explicit_no_future_or_legacy_autodetection(self):
        for version in (None, 1, "s01.input-manifest/v2", "pcie.triage-input/v1"):
            with self.subTest(version=version):
                doc = fixture()
                doc["schema_version"] = version
                self.assert_invalid(doc)
        doc = fixture()
        del doc["schema_version"]
        self.assert_invalid(doc)

    def test_known_fact_needs_value_and_evidence(self):
        for patch in ({"value": None}, {"evidence_refs": []}):
            with self.subTest(patch=patch):
                doc = fixture()
                doc["trace"]["facts"]["mode"].update(patch)
                self.assert_invalid(doc)

    def test_unknown_and_not_applicable_facts_cannot_carry_guessed_values(self):
        for state in ("unknown", "not_applicable"):
            for value in (False, "non-Flit", 0):
                with self.subTest(state=state, value=value):
                    doc = fixture()
                    doc["trace"]["facts"]["mode"].update(state=state, value=value)
                    self.assert_invalid(doc)

    def test_api_support_availability_and_observation_remain_separate(self):
        doc = fixture()
        doc["capabilities"][0].update(api_support="unsupported", availability="unavailable")
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(doc["observations"][0]["state"], "observed")
        assessment = contract.evaluate_profile(doc, profiles()["R-FIELD"])
        self.assertEqual(assessment["status"], "partial")
        condition = next(c for c in assessment["conditions"] if c["requirement"] == "field:pcie.AckNak_SeqNum")
        self.assertEqual(condition["status"], "missing")
        # The field is unavailable; an independently evidenced ACK event remains observed.
        self.assertEqual(contract.evaluate_profile(doc, profiles()["R-POSITIVE"])["status"], "eligible")

    def test_contradictory_capability_axes_are_rejected(self):
        patches = [
            {"api_support": "unsupported", "availability": "available"},
            {"api_support": "unknown", "availability": "available"},
            {"applicability": "not_applicable", "availability": "available"},
            {"applicability": "unknown", "availability": "available"},
            {"applicability": "applicable", "availability": "not_applicable"},
        ]
        for patch in patches:
            with self.subTest(patch=patch):
                doc = fixture()
                doc["capabilities"][0].update(patch)
                self.assert_invalid(doc)

    def test_supported_api_without_event_is_not_unsupported(self):
        doc = fixture()
        doc["observations"][0].update(state="not_observed_in_coverage", count=0)
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(doc["capabilities"][0]["api_support"], "supported")
        self.assertEqual(doc["capabilities"][0]["availability"], "available")

    def test_negative_observation_requires_each_coverage_prerequisite(self):
        invalid_values = {
            "selection": ("excluded", "unknown", "not_applicable"),
            "retention": ("dropped", "unknown", "not_applicable"),
            "extraction": ("partial", "unknown", "not_applicable"),
            "start_index": (None,),
            "end_index": (None,),
        }
        for key, values in invalid_values.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    doc = fixture()
                    doc["observations"][1]["coverage"][key] = value
                    self.assert_invalid(doc)
        doc = fixture()
        doc["trace"]["facts"]["filters"] = unknown_fact()
        self.assert_invalid(doc)

    def test_observed_event_survives_partial_extraction_and_unknown_filter(self):
        doc = fixture("unknown-filter.json")
        doc["observations"][0]["coverage"]["extraction"] = "partial"
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(contract.evaluate_profile(doc, profiles()["R-POSITIVE"])["status"], "eligible")
        self.assertEqual(contract.evaluate_profile(doc, profiles()["R-WINDOW"])["status"], "partial")

    def test_unknown_count_is_not_zero_and_zero_does_not_make_absence(self):
        for count in (None, 0):
            with self.subTest(count=count):
                doc = fixture()
                doc["observations"][1].update(state="unknown", count=count)
                before = copy.deepcopy(doc)
                self.assertEqual(contract.validate_manifest(doc), [])
                assessment = contract.evaluate_profile(doc, profiles()["R-WINDOW"])
                event = next(c for c in assessment["conditions"] if c["requirement"] == "event:pcie.NAK")
                self.assertEqual(event["status"], "unknown")
                self.assertEqual(doc, before)

    def test_event_states_and_counts_cannot_contradict_each_other(self):
        for state, count in (("observed", 0), ("observed", None), ("not_observed_in_coverage", 1),
                             ("not_observed_in_coverage", None), ("unknown", 2)):
            with self.subTest(state=state, count=count):
                doc = fixture()
                doc["observations"][0].update(state=state, count=count)
                self.assert_invalid(doc)

    def test_boolean_negative_fractional_and_string_counts_are_invalid(self):
        for value in (True, False, -1, 0.5, "0"):
            with self.subTest(value=value):
                doc = fixture()
                doc["observations"][0]["count"] = value
                self.assert_invalid(doc)

    def test_single_packet_range_is_valid_reversed_and_boolean_bounds_are_not(self):
        doc = fixture()
        doc["observations"][1]["coverage"].update(start_index=10, end_index=10)
        self.assertEqual(contract.validate_manifest(doc), [])
        for patch in ({"start_index": 21, "end_index": 20}, {"start_index": True}, {"end_index": False}):
            with self.subTest(patch=patch):
                doc = fixture()
                doc["observations"][1]["coverage"].update(patch)
                self.assert_invalid(doc)

    def test_not_applicable_event_requires_null_count_and_not_applicable_coverage(self):
        for key, value in (("count", 0), ("selection", "included"), ("retention", "retained"),
                           ("extraction", "complete"), ("start_index", 0), ("end_index", 0)):
            with self.subTest(key=key):
                doc = fixture("inapplicable.json")
                if key == "count":
                    doc["observations"][0][key] = value
                else:
                    doc["observations"][0]["coverage"][key] = value
                self.assert_invalid(doc)

    def test_all_reference_sites_require_resolution(self):
        for site in ("identity", "fact", "toolchain", "source", "capability", "event", "history"):
            with self.subTest(site=site):
                doc = fixture()
                targets = {
                    "identity": (doc["trace"], "identity_evidence_refs"),
                    "fact": (doc["trace"]["facts"]["mode"], "evidence_refs"),
                    "toolchain": (doc["toolchain"], "evidence_refs"),
                    "source": (doc["sources"][0], "evidence_refs"),
                    "capability": (doc["capabilities"][0], "evidence_refs"),
                    "event": (doc["observations"][0], "evidence_refs"),
                }
                doc["historical_claims"] = [{"claim": "PASS", "scope": "synthetic old scope", "evidence_refs": ["EV-S01"]}]
                targets["history"] = (doc["historical_claims"][0], "evidence_refs")
                target, key = targets[site]
                target[key] = ["DOES-NOT-EXIST"]
                self.assert_invalid(doc)

    def test_known_claims_cannot_be_supported_by_empty_refs(self):
        for site in ("identity", "fact", "toolchain", "capability", "event", "history"):
            with self.subTest(site=site):
                doc = fixture()
                doc["historical_claims"] = [{"claim": "PASS", "scope": "synthetic old scope", "evidence_refs": ["EV-S01"]}]
                targets = {
                    "identity": (doc["trace"], "identity_evidence_refs"),
                    "fact": (doc["trace"]["facts"]["mode"], "evidence_refs"),
                    "toolchain": (doc["toolchain"], "evidence_refs"),
                    "capability": (doc["capabilities"][0], "evidence_refs"),
                    "event": (doc["observations"][0], "evidence_refs"),
                    "history": (doc["historical_claims"][0], "evidence_refs"),
                }
                target, key = targets[site]
                target[key] = []
                self.assert_invalid(doc)

    def test_duplicate_evidence_sources_capabilities_and_event_ids_are_invalid(self):
        for collection in ("evidence", "sources", "capabilities", "observations"):
            with self.subTest(collection=collection):
                doc = fixture()
                doc[collection].append(copy.deepcopy(doc[collection][0]))
                self.assert_invalid(doc)

    def test_hidden_verdict_fields_are_rejected_but_historical_scope_is_preserved(self):
        for site in ("root", "trace", "capability", "event"):
            with self.subTest(site=site):
                doc = fixture()
                target = {"root": doc, "trace": doc["trace"], "capability": doc["capabilities"][0],
                          "event": doc["observations"][0]}[site]
                target["verified"] = True
                self.assert_invalid(doc)
        doc = fixture()
        doc["historical_claims"] = [{"claim": "PASS", "scope": "Prior synthetic extraction only", "evidence_refs": ["EV-S01"]}]
        before = copy.deepcopy(doc)
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(contract.evaluate_profile(doc, profiles()["R-MODE"])["qualification"], "NOT_EVALUATED")
        self.assertEqual(doc, before)

    def test_document_metadata_and_tool_versions_are_retained_without_runtime_claims(self):
        doc = fixture()
        doc["sources"][0].update(revision="13.40", review_depth="metadata_only", sections=[], applicability="unknown")
        doc["toolchain"]["software_version"] = "13.26"
        before = copy.deepcopy(doc)
        self.assertEqual(contract.validate_manifest(doc), [])
        self.assertEqual(contract.evaluate_profile(doc, profiles()["R-MODE"])["qualification"], "NOT_EVALUATED")
        self.assertEqual(doc, before)

    def test_recorded_positive_fields_and_events_cannot_use_document_only_evidence(self):
        for site in ("field", "observed_event", "negative_observation"):
            with self.subTest(site=site):
                doc = fixture()
                doc["origin"] = "recorded"
                doc["evidence"][0].update(kind="saved_output", trace_sha256=doc["trace"]["sha256"])
                doc["evidence"].append({"id": "EV-DOC", "kind": "document", "locator": "fixture://manual",
                                        "sha256": None, "note": "API support only; no trace observations."})
                doc["sources"][0]["evidence_refs"] = ["EV-DOC"]
                target = {"field": doc["capabilities"][0], "observed_event": doc["observations"][0],
                          "negative_observation": doc["observations"][1]}[site]
                target["evidence_refs"] = ["EV-DOC"]
                # The other claims retain good trace-bound refs, isolating this gate.
                self.assert_invalid(doc)

    def test_recorded_and_legacy_positive_evidence_must_bind_to_the_declared_trace(self):
        for origin in ("recorded", "legacy"):
            for kind in ("saved_output", "manual_review", "legacy"):
                with self.subTest(origin=origin, kind=kind):
                    doc = fixture()
                    doc["origin"] = origin
                    doc["evidence"][0].update(kind=kind, trace_sha256=doc["trace"]["sha256"])
                    self.assertEqual(contract.validate_manifest(doc), [])
                    wrong_trace = copy.deepcopy(doc)
                    wrong_trace["evidence"][0]["trace_sha256"] = "F" * 64
                    self.assert_invalid(wrong_trace)
                    unbound = copy.deepcopy(doc)
                    del unbound["evidence"][0]["trace_sha256"]
                    self.assert_invalid(unbound)

    def test_recorded_known_fact_cannot_use_document_even_with_other_good_trace_evidence(self):
        doc = fixture()
        doc["origin"] = "recorded"
        doc["evidence"][0].update(kind="saved_output", trace_sha256=doc["trace"]["sha256"])
        doc["evidence"].append({"id": "EV-DOC", "kind": "document", "locator": "fixture://manual",
                                "sha256": None, "note": "Describes support, does not observe this trace."})
        doc["trace"]["facts"]["mode"]["evidence_refs"] = ["EV-DOC"]
        self.assert_invalid(doc)

    def test_document_api_support_requires_matching_reviewed_applicable_source(self):
        doc = fixture()
        doc["evidence"].append({"id": "EV-DOC", "kind": "document", "locator": "fixture://manual",
                                "sha256": None, "note": "Synthetic reviewed section for API support only."})
        doc["sources"][0]["evidence_refs"] = ["EV-DOC"]
        doc["capabilities"][0].update(availability="unknown", evidence_refs=["EV-DOC"])
        # Availability is unknown so this positive case tests documented support only.
        self.assertEqual(contract.validate_manifest(doc), [])
        for patch in ({"review_depth": "metadata_only", "sections": []},
                      {"applicability": "not_applicable"}, {"applicability": "unknown"},
                      {"evidence_refs": ["EV-S01"]}):
            with self.subTest(source_patch=patch):
                bad = copy.deepcopy(doc)
                bad["sources"][0].update(patch)
                self.assert_invalid(bad)


class ReadinessTests(unittest.TestCase):
    def test_handwritten_expected_matrix_for_all_core_fixtures(self):
        all_profiles = profiles()
        for case in fixture("expected-readiness.json")["cases"]:
            manifest = fixture(case["file"])
            for slice_id, expected_status in case["expected"].items():
                with self.subTest(case=case["file"], profile=slice_id):
                    result = contract.evaluate_profile(manifest, all_profiles[slice_id])
                    self.assertEqual(result["slice_id"], slice_id)
                    self.assertEqual(result["status"], expected_status)
                    self.assertEqual(result["qualification"], "NOT_EVALUATED")
                    self.assertGreaterEqual(len(result["conditions"]), 4)
                    self.assertEqual([c["requirement"] for c in result["conditions"][:3]],
                                     ["trace.sha256", "trace.protocol", "fact:mode"])
                    for condition in result["conditions"]:
                        self.assertTrue(condition["reason"])
                        self.assertIsInstance(condition["evidence_refs"], list)

    def test_missing_aggregate_has_zero_met_and_a_known_mismatch(self):
        doc = fixture("all-unknown.json")
        doc["trace"]["facts"]["mode"] = {"state": "known", "value": "Flit", "evidence_refs": ["EV-S01"]}
        result = contract.evaluate_profile(doc, profiles()["R-FIELD"])
        self.assertEqual(result["status"], "missing")
        self.assertFalse(any(c["status"] == "met" for c in result["conditions"]))
        self.assertIn("missing", [c["status"] for c in result["conditions"]])

    def test_not_applicable_requirement_is_preserved_as_its_own_state(self):
        result = contract.evaluate_profile(fixture("inapplicable.json"), profiles()["R-FIELD"])
        field = next(c for c in result["conditions"] if c["requirement"] == "field:pcie.AckNak_SeqNum")
        self.assertEqual(field["status"], "not_applicable")
        self.assertNotEqual(result["status"], "eligible")

    def test_absent_field_and_event_remain_unknown_not_unsupported_or_zero(self):
        doc = fixture()
        doc["capabilities"] = []
        doc["observations"] = []
        for kind, identifier, expected in (("field", "pcie.AckNak_SeqNum", "available"),
                                            ("event", "pcie.ACK", "observed"),
                                            ("coverage", "pcie.ACK", "complete")):
            with self.subTest(kind=kind):
                result = contract.evaluate_profile(doc, one_profile(kind, identifier, expected))
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["conditions"][-1]["status"], "unknown")

    def test_exact_boolean_false_is_known_not_unknown_or_numeric_zero(self):
        doc = fixture()
        doc["trace"]["facts"]["bidirectional"]["value"] = False
        positive = contract.evaluate_profile(doc, one_profile("fact", "bidirectional", False))
        negative = contract.evaluate_profile(doc, one_profile("fact", "bidirectional", True))
        self.assertEqual(positive["status"], "eligible")
        self.assertEqual(negative["status"], "partial")
        self.assertEqual(negative["conditions"][-1]["status"], "missing")

    def test_invalid_profiles_do_not_get_vacuous_eligibility(self):
        cases = []
        p = profiles()["R-FIELD"]
        p["requirements"] = []
        cases.append(p)
        p = profiles()["R-FIELD"]
        p["modes"] = []
        cases.append(p)
        p = profiles()["R-FIELD"]
        del p["protocol"]
        cases.append(p)
        cases.extend([
            one_profile("fact", "not-a-known-fact", "known"),
            one_profile("field", "pcie.AckNak_SeqNum", "supported"),
            one_profile("event", "pcie.ACK", "absent"),
            one_profile("coverage", "pcie.ACK", "observed"),
        ])
        for profile in cases:
            with self.subTest(profile=profile):
                with self.assertRaises(contract.ContractError):
                    contract.evaluate_profile(fixture(), profile)

    def test_invalid_manifest_is_not_evaluated_as_ready(self):
        doc = fixture()
        doc["observations"][1]["coverage"]["selection"] = "unknown"
        with self.assertRaises(contract.ContractError):
            contract.evaluate_profile(doc, profiles()["R-MODE"])

    def test_readiness_is_deterministic_does_not_mutate_and_does_not_gain_from_irrelevant_docs(self):
        doc = fixture("missing-epoch.json")
        profile = profiles()["R-EPOCH"]
        before = copy.deepcopy((doc, profile))
        a = contract.evaluate_profile(doc, profile)
        b = contract.evaluate_profile(doc, profile)
        self.assertEqual(a, b)
        self.assertEqual((doc, profile), before)
        doc["sources"].append({**copy.deepcopy(doc["sources"][0]), "source_id": "ANOTHER-BACKGROUND-SOURCE"})
        self.assertEqual(contract.evaluate_profile(doc, profile)["status"], "partial")


class MatrixTests(unittest.TestCase):
    def make_matrix(self):
        return contract.build_matrix([fixture(), fixture("missing-epoch.json")],
                                     [profiles()["R-MODE"], profiles()["R-EPOCH"]])

    def test_build_matrix_reports_handwritten_readiness_not_qualification(self):
        manifests = [fixture(), fixture("missing-epoch.json")]
        selected_profiles = [profiles()["R-MODE"], profiles()["R-EPOCH"]]
        before = copy.deepcopy((manifests, selected_profiles))
        matrix = contract.build_matrix(manifests, selected_profiles)
        expected = [["eligible", "eligible"], ["eligible", "partial"]]
        self.assertEqual([[a["status"] for a in t["assessments"]] for t in matrix["traces"]], expected)
        self.assertEqual(matrix["claim_boundary"], "INPUT_ELIGIBILITY_ONLY")
        self.assertEqual(contract.validate_matrix(matrix), [])
        self.assertEqual((manifests, selected_profiles), before)
        for trace in matrix["traces"]:
            self.assertTrue(all(a["qualification"] == "NOT_EVALUATED" for a in trace["assessments"]))

    def test_matrix_cannot_hide_stale_or_forged_assessments(self):
        mutations = [
            lambda m: m["traces"][1]["assessments"][1].update(status="eligible"),
            lambda m: m["traces"][0]["assessments"][0].update(qualification="PASS"),
            lambda m: m["traces"][0]["assessments"][0]["conditions"][0].update(status="unknown"),
            lambda m: m["traces"][0]["assessments"][0]["conditions"][0].update(evidence_refs=["DANGLING"]),
            lambda m: m["traces"][0]["assessments"].pop(),
            lambda m: m["traces"][0]["assessments"][0].update(slice_id="NOT-A-PROFILE"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                matrix = self.make_matrix()
                mutate(matrix)
                self.assertTrue(contract.validate_matrix(matrix))

    def test_matrix_revalidates_embedded_manifests_and_schema(self):
        for mutate in (
            lambda m: m.update(schema_version="s01.trace-eligibility/v2"),
            lambda m: m.update(protocol_verdict="PASS"),
            lambda m: m["traces"][0]["manifest"].update(verified=True),
            lambda m: m["profiles"][0].update(requirements=[]),
            lambda m: m["profiles"].append(copy.deepcopy(m["profiles"][0])),
        ):
            matrix = self.make_matrix()
            mutate(matrix)
            self.assertTrue(contract.validate_matrix(matrix))


class LegacyAndCliTests(unittest.TestCase):
    def test_legacy_views_preserve_original_claims_and_bytes_without_opening_raw_files(self):
        cases = [("legacy-pcie.json", "pcie.triage-input/v1", ["D" * 64]),
                 ("legacy-usb.json", "usb.demo-source-integrity", ["1" * 64, "2" * 64])]
        for name, legacy_format, expected_hashes in cases:
            with self.subTest(name=name):
                path = FIXTURES / name
                raw = path.read_bytes()
                original = json.loads(raw)
                result = contract.legacy_view(path, legacy_format)
                self.assertEqual(result["original"], original)
                self.assertEqual(result["artifact_sha256"].lower(), hashlib.sha256(raw).hexdigest())
                self.assertEqual(result["coverage"], "unknown")
                self.assertEqual(result["qualification"], "NOT_EVALUATED")
                self.assertEqual(result["raw_trace_access"], "not_checked")
                serialized_identities = json.dumps(result["trace_identities"])
                for expected in expected_hashes:
                    self.assertIn(expected, serialized_identities)
                self.assertEqual(path.read_bytes(), raw)

    def test_legacy_format_is_explicit_and_wrong_shapes_are_rejected(self):
        for name, legacy_format in (("legacy-pcie.json", "unknown-format"),
                                    ("legacy-pcie.json", "usb.demo-source-integrity"),
                                    ("legacy-usb.json", "pcie.triage-input/v1")):
            with self.subTest(name=name, legacy_format=legacy_format):
                with self.assertRaises(contract.ContractError):
                    contract.legacy_view(FIXTURES / name, legacy_format)

    def run_cli(self, *args, cwd):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "s01_contract.py"), *map(str, args)],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=30)

    def test_cli_validates_manifest_and_prints_json_without_writing_files(self):
        with tempfile.TemporaryDirectory(prefix="s01-cli-") as directory:
            root = Path(directory)
            path = root / "manifest.json"
            path.write_bytes((FIXTURES / "complete-pcie.json").read_bytes())
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = self.run_cli("manifest", path, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)

    def test_cli_invalid_manifest_exits_two_and_preserves_input(self):
        with tempfile.TemporaryDirectory(prefix="s01-cli-") as directory:
            root = Path(directory)
            path = root / "invalid.json"
            doc = fixture()
            doc["claim_boundary"] = "PROTOCOL_PASS"
            path.write_text(json.dumps(doc), encoding="utf-8")
            before = path.read_bytes()
            result = self.run_cli("manifest", path, cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["invalid.json"])

    def test_cli_matrix_and_legacy_do_not_run_or_qualify_trace(self):
        with tempfile.TemporaryDirectory(prefix="s01-cli-") as directory:
            root = Path(directory)
            matrix_path = root / "matrix.json"
            matrix = contract.build_matrix([fixture()], [profiles()["R-MODE"]])
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            before = matrix_path.read_bytes()
            result = self.run_cli("matrix", matrix_path, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIsInstance(json.loads(result.stdout), dict)
            result = self.run_cli("legacy", FIXTURES / "legacy-pcie.json", "--legacy-format", "pcie.triage-input/v1", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            view = json.loads(result.stdout)
            self.assertEqual(view["qualification"], "NOT_EVALUATED")
            self.assertEqual(view["raw_trace_access"], "not_checked")
            self.assertEqual(matrix_path.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["matrix.json"])

    def test_legacy_json_finite_overflow_is_contract_error_and_cli_exit_two(self):
        with tempfile.TemporaryDirectory(prefix="s01-legacy-overflow-") as directory:
            root = Path(directory)
            path = root / "legacy-overflow.json"
            # 1e400 is a legal JSON number, but must not become an Infinity value
            # which later crashes strict serialization or leaks into the view.
            raw = json.dumps(fixture("legacy-pcie.json"))[:-1] + ', "oversized_number": 1e400}'
            path.write_text(raw, encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(contract.ContractError):
                contract.legacy_view(path, "pcie.triage-input/v1")
            result = self.run_cli("legacy", path, "--legacy-format", "pcie.triage-input/v1", cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["legacy-overflow.json"])


if __name__ == "__main__":
    unittest.main()
