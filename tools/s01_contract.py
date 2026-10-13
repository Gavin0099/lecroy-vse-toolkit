#!/usr/bin/env python3
"""Standalone S01 metadata validation. Never imports or runs either pipeline.

The schema walker implements only the vocabulary used by the two bundled S01
schemas. It is not a general JSON Schema implementation. JSON references never
cause network access, and evidence locators never cause trace/file access.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
MANIFEST_SCHEMA = "s01-input-manifest-v1.schema.json"
MATRIX_SCHEMA = "s01-trace-eligibility-v1.schema.json"
FACTS = {"mode", "bidirectional", "capture_start", "capture_end", "epoch", "filters"}
HASH = re.compile(r"^[0-9A-Fa-f]{64}$")


class ContractError(ValueError):
    """Malformed input, unsupported format, or an inconsistent contract."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bad_constant(value):
    raise ContractError(f"non-JSON numeric constant: {value}")


def _finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ContractError("JSON number exceeds finite float range")
    return parsed


def read_json(path: Path):
    """Read exactly the named JSON file; never follow an evidence locator."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_pairs, parse_constant=_bad_constant, parse_float=_finite_float)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ContractError(str(exc)) from exc


def _schema(name):
    return read_json(SCHEMA_DIR / name)


def _error(errors, code, path, message):
    errors.append({"code": code, "path": path, "message": message})


def _equal(left, right):
    # JSON booleans must not compare equal to 0/1.
    return type(left) is type(right) and left == right


def _walk(value, schema, root, path, errors):
    supported = {"$schema", "$id", "title", "$defs", "$ref", "type", "enum",
                 "const", "required", "properties", "additionalProperties",
                 "items", "minItems", "minLength", "minimum", "pattern", "anyOf"}
    if set(schema) - supported:
        raise ContractError(f"unsupported S01 schema keyword: {set(schema) - supported}")
    if "$ref" in schema:
        reference = schema["$ref"]
        if reference.startswith("#/$defs/"):
            return _walk(value, root["$defs"][reference[8:]], root, path, errors)
        if reference == MANIFEST_SCHEMA:
            external = _schema(MANIFEST_SCHEMA)
            return _walk(value, external, external, path, errors)
        raise ContractError(f"unsupported schema reference: {reference}")
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            trial = []
            _walk(value, option, root, path, trial)
            if not trial:
                return
        _error(errors, "SCHEMA", path, "value does not match any permitted type")
        return
    kind = schema.get("type")
    kinds = {"object": dict, "array": list, "string": str, "integer": int,
             "boolean": bool, "null": type(None)}
    if kind and (kind not in kinds or type(value) is not kinds[kind]):
        _error(errors, "SCHEMA", path, f"expected {kind}")
        return
    if "const" in schema and not _equal(value, schema["const"]):
        _error(errors, "SCHEMA", path, "constant mismatch")
    if "enum" in schema and not any(_equal(value, x) for x in schema["enum"]):
        _error(errors, "SCHEMA", path, "value is not in the permitted enum")
    if type(value) is dict:
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                _error(errors, "SCHEMA", path + "/" + key, "required key is missing")
        for key, child in value.items():
            if key in props:
                _walk(child, props[key], root, path + "/" + key, errors)
            elif schema.get("additionalProperties") is False:
                _error(errors, "SCHEMA", path + "/" + key, "undeclared key is forbidden")
    if type(value) is list:
        if len(value) < schema.get("minItems", 0):
            _error(errors, "SCHEMA", path, "too few items")
        for index, child in enumerate(value):
            if "items" in schema:
                _walk(child, schema["items"], root, f"{path}/{index}", errors)
    if type(value) is str:
        if len(value) < schema.get("minLength", 0):
            _error(errors, "SCHEMA", path, "string is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            _error(errors, "SCHEMA", path, "string pattern mismatch")
    if type(value) is int and "minimum" in schema and value < schema["minimum"]:
        _error(errors, "SCHEMA", path, "integer is below minimum")


def _structure(value, name):
    errors = []
    schema = _schema(name)
    _walk(value, schema, schema, "", errors)
    return errors


def _unique(rows, key, path, errors):
    seen = set()
    for i, row in enumerate(rows):
        if row[key] in seen:
            _error(errors, "DUPLICATE_ID", f"{path}/{i}/{key}", "ID must be unique")
        seen.add(row[key])


def _refs(value, known, path, errors):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("evidence_refs"):
                if len(child) != len(set(child)):
                    _error(errors, "DUPLICATE_REF", path + "/" + key, "duplicate evidence reference")
                for entry in child:
                    if entry not in known:
                        _error(errors, "UNRESOLVED_REF", path + "/" + key, f"unknown evidence ID: {entry}")
            else:
                _refs(child, known, path + "/" + key, errors)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _refs(child, known, f"{path}/{i}", errors)


def _needs_refs(refs, path, errors):
    if not refs:
        _error(errors, "EVIDENCE_REQUIRED", path, "a stated fact requires a source reference")


def _observational_refs(document, refs, path, errors):
    """A document may describe an API, but cannot observe this trace for us."""
    trace_sha = document["trace"]["sha256"]
    for evidence in document["evidence"]:
        if evidence["id"] not in refs:
            continue
        if document["origin"] == "synthetic" and evidence["kind"] == "synthetic":
            return
        bound_sha = evidence.get("trace_sha256")
        if (evidence["kind"] in {"saved_output", "manual_review", "legacy"}
                and trace_sha is not None and bound_sha is not None
                and trace_sha.lower() == bound_sha.lower()):
            return
    _error(errors, "OBSERVATIONAL_EVIDENCE_REQUIRED", path,
           "requires same-trace saved output/manual review/legacy reference; documentation alone is insufficient")


def _api_refs(document, refs, path, errors):
    trial = []
    _observational_refs(document, refs, path, trial)
    if not trial:
        return
    document_refs = {e["id"] for e in document["evidence"] if e["kind"] == "document" and e["id"] in refs}
    for source in document["sources"]:
        if (source["applicability"] == "applicable" and source["review_depth"] == "sections_reviewed"
                and source["sections"] and document_refs.intersection(source["evidence_refs"])):
            return
    _error(errors, "API_SOURCE_REQUIRED", path,
           "API support requires applicable reviewed documentation or same-trace observational evidence")


def coverage_complete(manifest, observation):
    """Complete only inside the declared inclusive packet-index window."""
    coverage = observation["coverage"]
    return (coverage["selection"] == "included" and coverage["retention"] == "retained"
            and coverage["extraction"] == "complete"
            and coverage["start_index"] is not None and coverage["end_index"] is not None
            and coverage["start_index"] <= coverage["end_index"]
            and manifest["trace"]["facts"]["filters"]["state"] == "known")


def validate_manifest(document: Any) -> list[dict]:
    errors = _structure(document, MANIFEST_SCHEMA)
    if errors:
        return errors
    for field, key in [("evidence", "id"), ("sources", "source_id"),
                       ("capabilities", "id"), ("observations", "event")]:
        _unique(document[field], key, "/" + field, errors)
    refs = {e["id"] for e in document["evidence"]}
    _refs(document, refs, "", errors)
    if document["origin"] == "recorded" and any(e["kind"] == "synthetic" for e in document["evidence"]):
        _error(errors, "SYNTHETIC_NOT_RECORDED", "/origin", "synthetic references cannot establish recorded input")
    trace = document["trace"]
    if trace["sha256"] is not None or trace["protocol"] != "unknown":
        _needs_refs(trace["identity_evidence_refs"], "/trace/identity_evidence_refs", errors)
        _observational_refs(document, trace["identity_evidence_refs"], "/trace/identity_evidence_refs", errors)
    for key, fact in trace["facts"].items():
        path = "/trace/facts/" + key
        if fact["state"] == "known":
            _needs_refs(fact["evidence_refs"], path, errors)
            _observational_refs(document, fact["evidence_refs"], path, errors)
            value = fact["value"]
            good = type(value) is bool if key == "bidirectional" else type(value) is str and bool(value.strip())
            if key in {"capture_start", "capture_end"}:
                good = value in {"complete", "partial"}
            if not good:
                _error(errors, "FACT_VALUE", path, "known fact has an invalid or absent value")
        elif fact["value"] is not None:
            _error(errors, "UNKNOWN_NOT_VALUE", path, "unknown/not_applicable must retain null, not a guessed value")
        if fact["state"] == "not_applicable":
            _needs_refs(fact["evidence_refs"], path, errors)
    toolchain = document["toolchain"]
    if any(toolchain[k] is not None for k in ["software_version", "extractor_sha256", "constants_sha256"]):
        _needs_refs(toolchain["evidence_refs"], "/toolchain", errors)
    for i, source in enumerate(document["sources"]):
        _needs_refs(source["evidence_refs"], f"/sources/{i}", errors)
        if source["review_depth"] == "sections_reviewed" and not source["sections"]:
            _error(errors, "SECTIONS_REQUIRED", f"/sources/{i}", "selected-section review needs exact sections")
    for i, cap in enumerate(document["capabilities"]):
        path = f"/capabilities/{i}"
        if any(cap[k] != "unknown" for k in ["api_support", "applicability", "availability"]):
            _needs_refs(cap["evidence_refs"], path, errors)
        if cap["api_support"] in {"supported", "unsupported"}:
            _api_refs(document, cap["evidence_refs"], path, errors)
        if cap["availability"] in {"available", "unavailable"}:
            _observational_refs(document, cap["evidence_refs"], path, errors)
        if cap["availability"] == "available" and (cap["api_support"] != "supported" or cap["applicability"] != "applicable"):
            _error(errors, "CAPABILITY_CONFLICT", path, "available requires supported and applicable")
        if (cap["availability"] == "not_applicable") != (cap["applicability"] == "not_applicable"):
            _error(errors, "CAPABILITY_CONFLICT", path, "not_applicable must be explicit on both applicability and availability")
    for i, obs in enumerate(document["observations"]):
        path = f"/observations/{i}"
        state, count, cov = obs["state"], obs["count"], obs["coverage"]
        if (state != "unknown" or count is not None
                or any(cov[k] != "unknown" for k in ["selection", "retention", "extraction"])
                or any(cov[k] is not None for k in ["start_index", "end_index"])):
            _needs_refs(obs["evidence_refs"], path, errors)
            if state != "not_applicable":
                _observational_refs(document, obs["evidence_refs"], path, errors)
        if cov["start_index"] is not None and cov["end_index"] is not None and cov["start_index"] > cov["end_index"]:
            _error(errors, "RANGE_ORDER", path, "start_index exceeds end_index")
        if state == "observed" and (count is None or count <= 0 or cov["selection"] in {"excluded", "not_applicable"}):
            _error(errors, "OBSERVATION_CONFLICT", path, "observed requires positive count and cannot be excluded")
        if state == "not_observed_in_coverage" and (count != 0 or not coverage_complete(document, obs)):
            _error(errors, "ABSENCE_UNPROVEN", path, "zero events needs selected/retained/complete extraction, known filters and bounded range")
        if state == "unknown" and count not in (None, 0):
            _error(errors, "OBSERVATION_CONFLICT", path, "positive count is observed, not unknown")
        if state == "not_applicable":
            if count is not None or any(cov[k] != "not_applicable" for k in ["selection", "retention", "extraction"]) or any(cov[k] is not None for k in ["start_index", "end_index"]):
                _error(errors, "OBSERVATION_CONFLICT", path, "inapplicable event has null count/range and inapplicable coverage")
        elif any(cov[k] == "not_applicable" for k in ["selection", "retention", "extraction"]):
            _error(errors, "OBSERVATION_CONFLICT", path, "inapplicable coverage requires inapplicable event")
    for i, claim in enumerate(document["historical_claims"]):
        _needs_refs(claim["evidence_refs"], f"/historical_claims/{i}", errors)
    return errors


def _validate_profile(profile):
    errors = []
    schema = _schema(MATRIX_SCHEMA)
    _walk(profile, schema["$defs"]["profile"], schema, "", errors)
    if errors:
        return errors
    seen = set()
    for i, req in enumerate(profile["requirements"]):
        kind, key, expected = req["kind"], req["id"], req["expected"]
        if (kind, key) in seen:
            _error(errors, "DUPLICATE_REQUIREMENT", f"/requirements/{i}", "each kind/id has one requirement")
        seen.add((kind, key))
        if kind == "fact":
            valid = key in FACTS
            if key == "bidirectional":
                valid &= type(expected) is bool or expected == "known"
            elif key in {"capture_start", "capture_end"}:
                valid &= expected in {"known", "complete", "partial"}
            else:
                valid &= type(expected) is str
        else:
            valid = expected in {"field": ["available"], "event": ["observed", "not_observed_in_coverage"], "coverage": ["complete"]}[kind]
        if not valid:
            _error(errors, "REQUIREMENT_INVALID", f"/requirements/{i}", "unsupported requirement key or expected value")
    return errors


def _assessment(document, profile):
    trace = document["trace"]
    conditions = [{"requirement": "trace.sha256", "status": "met" if trace["sha256"] else "unknown",
                   "reason": "declared trace identity present" if trace["sha256"] else "trace identity unknown",
                   "evidence_refs": trace["identity_evidence_refs"]}]
    protocol_status = "unknown" if trace["protocol"] == "unknown" else "met" if trace["protocol"] == profile["protocol"] else "missing"
    conditions.append({"requirement": "trace.protocol", "status": protocol_status,
                       "reason": "declared protocol compared with profile; unknown is not a match",
                       "evidence_refs": trace["identity_evidence_refs"]})
    mode = trace["facts"]["mode"]
    mode_status = ("not_applicable" if mode["state"] == "not_applicable" else "unknown" if mode["state"] == "unknown"
                   else "met" if mode["value"] in profile["modes"] else "missing")
    conditions.append({"requirement": "fact:mode", "status": mode_status,
                       "reason": "declared mode compared with explicit profile modes",
                       "evidence_refs": mode["evidence_refs"]})
    caps = {c["id"]: c for c in document["capabilities"]}
    observations = {o["event"]: o for o in document["observations"]}
    for req in profile["requirements"]:
        kind, key, expected = req["kind"], req["id"], req["expected"]
        status, reason, refs = "unknown", "required metadata was not supplied", []
        if kind == "fact":
            fact = trace["facts"][key]
            refs = fact["evidence_refs"]
            if fact["state"] == "not_applicable":
                status, reason = "not_applicable", "fact explicitly not applicable"
            elif fact["state"] == "known":
                status = "met" if expected == "known" or _equal(expected, fact["value"]) else "missing"
                reason = "known fact meets requirement" if status == "met" else "known fact does not meet requirement"
        elif kind == "field" and key in caps:
            cap = caps[key]
            refs = cap["evidence_refs"]
            if cap["applicability"] == "not_applicable":
                status, reason = "not_applicable", "field is not applicable"
            elif cap["api_support"] == "unsupported":
                status, reason = "missing", "API explicitly unsupported"
            elif cap["availability"] == "unavailable":
                status, reason = "missing", "field explicitly unavailable"
            elif cap["availability"] == "available":
                status, reason = "met", "field supported, applicable and available"
        elif kind in {"event", "coverage"} and key in observations:
            obs = observations[key]
            refs = obs["evidence_refs"]
            if obs["state"] == "not_applicable":
                status, reason = "not_applicable", "event is not applicable"
            elif kind == "coverage":
                if coverage_complete(document, obs):
                    status, reason = "met", "known coverage within inclusive index window"
                elif (obs["coverage"]["selection"] == "excluded" or obs["coverage"]["retention"] == "dropped" or obs["coverage"]["extraction"] == "partial"):
                    status, reason = "missing", "coverage is explicitly excluded, dropped or partial"
                else:
                    reason = "selection/retention/extraction/filter/range is unknown"
            elif obs["state"] != "unknown":
                status = "met" if obs["state"] == expected else "missing"
                reason = "observed state meets requirement" if status == "met" else "observed state differs from requirement"
        conditions.append({"requirement": kind + ":" + key, "status": status, "reason": reason, "evidence_refs": refs})
    statuses = [c["status"] for c in conditions]
    if all(s == "met" for s in statuses):
        result = "eligible"
    elif "met" in statuses:
        result = "partial"
    elif any(s in {"missing", "not_applicable"} for s in statuses):
        result = "missing"
    else:
        result = "unknown"
    return {"slice_id": profile["slice_id"], "status": result, "conditions": conditions, "qualification": "NOT_EVALUATED"}


def evaluate_profile(document, profile):
    errors = validate_manifest(document) + _validate_profile(profile)
    if errors:
        raise ContractError(json.dumps(errors, ensure_ascii=False))
    return _assessment(document, profile)


def validate_matrix(document):
    errors = _structure(document, MATRIX_SCHEMA)
    if errors:
        return errors
    _unique(document["profiles"], "slice_id", "/profiles", errors)
    for i, profile in enumerate(document["profiles"]):
        for error in _validate_profile(profile):
            error["path"] = f"/profiles/{i}" + error["path"]
            errors.append(error)
    if errors:
        return errors
    manifest_ids, trace_ids = set(), set()
    for i, row in enumerate(document["traces"]):
        manifest = row["manifest"]
        row_errors = validate_manifest(manifest)
        for error in row_errors:
            error["path"] = f"/traces/{i}/manifest" + error["path"]
            errors.append(error)
        if manifest["manifest_id"] in manifest_ids or manifest["trace"]["trace_id"] in trace_ids:
            _error(errors, "DUPLICATE_ID", f"/traces/{i}", "trace and manifest IDs must be unique in this matrix")
        manifest_ids.add(manifest["manifest_id"])
        trace_ids.add(manifest["trace"]["trace_id"])
        if not row_errors:
            expected = [_assessment(manifest, p) for p in document["profiles"]]
            if row["assessments"] != expected:
                _error(errors, "ELIGIBILITY_MISMATCH", f"/traces/{i}/assessments", "recomputed conditions/status must match; eligibility cannot be asserted manually")
    return errors


def build_matrix(manifests, profiles):
    result = {"schema_version": "s01.trace-eligibility/v1", "profiles": copy.deepcopy(profiles),
              "traces": [{"manifest": copy.deepcopy(m), "assessments": [evaluate_profile(m, p) for p in profiles]} for m in manifests],
              "claim_boundary": "INPUT_ELIGIBILITY_ONLY"}
    errors = validate_matrix(result)
    if errors:
        raise ContractError(json.dumps(errors, ensure_ascii=False))
    return result


def legacy_view(path: Path, legacy_format: str):
    """Inspect a saved JSON without modifying it or following any of its paths.

    Shape recognition is NOT rerunning the legacy validator or requalifying PASS.
    All original values, including contradictory historical claims, are retained.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
        original = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                              parse_constant=_bad_constant, parse_float=_finite_float)
        if type(original) is not dict:
            raise ContractError("legacy document must be an object")
        identities = []

        def identity(pointer, role, value):
            if type(value) is not str or HASH.fullmatch(value) is None:
                raise ContractError(f"invalid declared trace hash at {pointer}")
            identities.append({"role": role, "json_pointer": pointer, "sha256": value})

        if legacy_format == "pcie.triage-input/v1":
            if original.get("schema_version") != legacy_format:
                raise ContractError("unsupported legacy schema version")
            identity("/trace/sha256", "analysis_trace", original["trace"]["sha256"])
            provenance = original["trace"].get("provenance", {})
            if "original_sha256" in provenance:
                identity("/trace/provenance/original_sha256", "original_trace", provenance["original_sha256"])
        elif legacy_format == "usb.demo-source-integrity":
            if "schema_version" in original:
                raise ContractError("USB compatibility reader only accepts the documented unversioned shape")
            for role in ["pass", "fail"]:
                for when in ["before", "after"]:
                    identity(f"/{role}/{when}/sha256", f"source_{role}_{when}", original[role][when]["sha256"])
                    identity(f"/working_copy/{role}/{when}/sha256", f"working_copy_{role}_{when}", original["working_copy"][role][when]["sha256"])
        else:
            raise ContractError("unsupported explicit legacy format")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ContractError(f"invalid legacy input: {exc}") from exc
    return {"schema_version": "s01.legacy-view/v1", "legacy_format": legacy_format,
            "artifact_sha256": hashlib.sha256(raw).hexdigest(), "original": original,
            "trace_identities": identities, "identity_verification": "saved_json_only",
            "coverage": "unknown", "qualification": "NOT_EVALUATED", "raw_trace_access": "not_checked"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["manifest", "matrix", "legacy"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--legacy-format", choices=["pcie.triage-input/v1", "usb.demo-source-integrity"])
    args = parser.parse_args(argv)
    try:
        if args.kind == "legacy":
            if not args.legacy_format:
                raise ContractError("legacy requires an explicit --legacy-format")
            result = legacy_view(args.path, args.legacy_format)
        else:
            document = read_json(args.path)
            errors = (validate_manifest if args.kind == "manifest" else validate_matrix)(document)
            result = {"schema_version": "s01.validation/v1", "status": "invalid" if errors else "valid",
                      "scope": "metadata_consistency_only", "errors": errors, "qualification": "NOT_EVALUATED"}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result.get("status") == "invalid" else 0
    except ContractError as exc:
        print(json.dumps({"status": "invalid", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}], "qualification": "NOT_EVALUATED"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
