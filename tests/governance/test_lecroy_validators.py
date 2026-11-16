"""Focused harness for the LeCroy domain validators (G1-3).

Expected outcomes come from governance/rules/lecroy/trace_integrity.md, not
from the validator code: each fail fixture must fail for the rule it targets,
each pass fixture must pass, and the contract must turn only the TRACE rules
into hard stops. The framework's own loaders run the validators, as the
post-task check would.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / "ai-governance-framework"
CONTRACT = REPO / "contract.yaml"
FIXTURES = REPO / "governance" / "validators" / "fixtures"

if not (FRAMEWORK / "governance_tools").is_dir():
    pytest.skip("ai-governance-framework submodule is not checked out", allow_module_level=True)
sys.path.insert(0, str(FRAMEWORK))

from governance_tools.consumer_fixture_runner import build_consumer_fixture_report  # noqa: E402
from governance_tools.domain_contract_loader import load_domain_contract  # noqa: E402
from governance_tools.domain_validator_loader import (  # noqa: E402
    build_domain_validation_payload,
    discover_domain_validators,
    run_domain_validators,
)
from runtime_hooks.core.post_task_check import (  # noqa: E402
    _classify_domain_policy_inputs,
    _domain_hard_stop_rules,
)

# fixture -> (expected ok, violation code that must appear when it fails)
SPEC = {
    "trace_capture_violation": (False, "LECROY-TRACE-001"),
    "trace_capture_compliant": (True, None),
    "trace_capture_with_decision": (True, None),
    "trace_identity_missing": (False, "LECROY-TRACE-002"),
    "trace_identity_preserved": (True, None),
    "trace_identity_mismatch": (False, "LECROY-TRACE-002"),
    "trace_identity_not_applicable": (True, None),
    "deletion_missing_scope": (False, "LECROY-DEL-001"),
    "deletion_with_scope": (True, None),
    "deletion_tests_only": (True, None),
}
VALIDATOR_FOR = {
    "trace": "lecroy_trace_integrity_validator",
    "deletion": "lecroy_deletion_scope_validator",
}


def _run(name: str, active_rules: list[str] | None = None) -> list[dict]:
    checks = json.loads((FIXTURES / f"{name}.checks.json").read_text(encoding="utf-8"))
    rules = active_rules if active_rules is not None else ["common", "lecroy"]
    payload = build_domain_validation_payload(
        response_text="",
        checks=checks,
        fields={},
        resolved_rules=rules,
        domain_contract=load_domain_contract(CONTRACT),
        contract_file=CONTRACT,
    )
    return run_domain_validators(contract_file=CONTRACT, payload=payload, active_rule_ids=rules)


def _result_for(name: str) -> dict:
    wanted = VALIDATOR_FOR[name.split("_", 1)[0]]
    matches = [item for item in _run(name) if item["name"] == wanted]
    assert len(matches) == 1, f"{wanted} did not run for {name}"
    return matches[0]


def test_contract_declares_both_validators_and_they_load():
    discovered = {item["name"]: item for item in discover_domain_validators(CONTRACT)}
    assert set(discovered) == set(VALIDATOR_FOR.values())
    for item in discovered.values():
        assert item["ok"], item["errors"]
        assert "lecroy" in item["rule_ids"]


@pytest.mark.parametrize("name", sorted(SPEC))
def test_fixture_matches_rule_spec(name):
    expected_ok, code = SPEC[name]
    result = _result_for(name)
    assert result["ok"] is expected_ok, result
    if code:
        assert result["violations"], result
        assert all(v.startswith(code) for v in result["violations"]), result["violations"]
    else:
        assert result["violations"] == []


def test_mismatch_names_the_changed_trace():
    violations = _result_for("trace_identity_mismatch")["violations"]
    assert violations == [
        "LECROY-TRACE-002: input trace changed (sha256 before != after): dp1 hub detect SSD fail-2.usb"
    ]


def test_backslash_capture_path_is_still_caught():
    violations = _result_for("trace_capture_violation")["violations"]
    assert len(violations) == 2


def test_not_applicable_declaration_is_visible_as_warning():
    warnings = _result_for("trace_identity_not_applicable")["warnings"]
    assert len(warnings) == 1 and warnings[0].startswith("LECROY-TRACE-002")


def test_only_trace_rules_are_hard_stops():
    hard_stop = _domain_hard_stop_rules(load_domain_contract(CONTRACT))
    assert hard_stop == {"LECROY-TRACE-001", "LECROY-TRACE-002"}

    trace_stops = _classify_domain_policy_inputs(
        [_result_for("trace_identity_mismatch")], hard_stop_rules=hard_stop
    )
    assert len(trace_stops) == 1 and trace_stops[0]["source"] == "hard_stop_rules"

    deletion_stops = _classify_domain_policy_inputs(
        [_result_for("deletion_missing_scope")], hard_stop_rules=hard_stop
    )
    assert deletion_stops == []


def test_validators_do_not_run_unless_lecroy_rule_is_active():
    assert _run("trace_identity_mismatch", active_rules=["common"]) == []


def test_framework_fixture_runner_matches_every_fixture():
    report = build_consumer_fixture_report(REPO, contract=CONTRACT)
    assert report.errors == []
    assert report.overall_status == "all_expected"
    assert report.fixtures_total == len(SPEC)
    assert report.mismatched_expectations == 0
