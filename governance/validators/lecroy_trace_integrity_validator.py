#!/usr/bin/env python3
"""LeCroy trace integrity validator (rules LECROY-TRACE-001 and LECROY-TRACE-002).

See governance/rules/lecroy/trace_integrity.md for the rule text. The validator
checks evidence supplied in the post-task ``checks`` object; it cannot prove on
its own that a trace was left untouched.
"""

from __future__ import annotations

import fnmatch
import re

from governance_tools.validator_interface import DomainValidator, ValidatorResult

CAPTURE_EXTENSIONS = (".usb", ".usbtrace", ".uwb", ".utp", ".pex")

TRACE_OPENER_PATTERNS = (
    "*.vse",
    "*.pevs",
    "tools/*.cs",
    "tools/run-*.ps1",
    "tools/start-*.ps1",
    "tools/run-*.py",
    "tools/*_probe.py",
    "tools/u01_selection.py",
    "tools/usb_triage_pipeline.py",
    "scripts/pcie/com_*.py",
    "scripts/pcie/a1_com_*.py",
    "scripts/pcie/run_pcie_triage.py",
)

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _normalize(path: object) -> str:
    text = str(path).strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _is_capture(path: str) -> bool:
    return path.lower().endswith(CAPTURE_EXTENSIONS)


def _is_trace_opener(path: str) -> bool:
    lowered = path.lower()
    if lowered.startswith("tests/") or lowered.endswith(".md"):
        return False
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in TRACE_OPENER_PATTERNS)


class LeCroyTraceIntegrityValidator(DomainValidator):
    @property
    def rule_ids(self) -> list[str]:
        return ["lecroy", "LECROY-TRACE-001", "LECROY-TRACE-002"]

    def validate(self, payload: dict) -> ValidatorResult:
        checks = payload.get("checks") or {}
        changed = [_normalize(item) for item in payload.get("changed_files") or [] if str(item).strip()]
        violations: list[str] = []
        warnings: list[str] = []

        decisions_raw = checks.get("trace_capture_decisions") or {}
        decisions = (
            {_normalize(key): str(value).strip() for key, value in decisions_raw.items()}
            if isinstance(decisions_raw, dict)
            else {}
        )
        captures = [path for path in changed if _is_capture(path)]
        for path in captures:
            if not decisions.get(path):
                violations.append(
                    f"LECROY-TRACE-001: trace capture in change set without a recorded handling decision: {path}"
                )

        openers = [path for path in changed if _is_trace_opener(path)]
        identity = checks.get("trace_identity")
        not_applicable = str(checks.get("trace_identity_not_applicable") or "").strip()
        identity_ok_entries = 0

        if identity is not None:
            if not isinstance(identity, list) or not identity:
                violations.append("LECROY-TRACE-002: trace_identity must be a non-empty list")
            else:
                for index, entry in enumerate(identity):
                    label = entry.get("trace", f"#{index}") if isinstance(entry, dict) else f"#{index}"
                    if not isinstance(entry, dict):
                        violations.append(f"LECROY-TRACE-002: trace_identity entry {label} is not an object")
                        continue
                    before = str(entry.get("before_sha256") or "")
                    after = str(entry.get("after_sha256") or "")
                    if not (_SHA256.match(before) and _SHA256.match(after)):
                        violations.append(
                            f"LECROY-TRACE-002: trace_identity entry {label} needs 64-hex before_sha256 and after_sha256"
                        )
                        continue
                    if before.lower() != after.lower():
                        violations.append(f"LECROY-TRACE-002: input trace changed (sha256 before != after): {label}")
                        continue
                    if "before_size" in entry or "after_size" in entry:
                        if entry.get("before_size") != entry.get("after_size"):
                            violations.append(f"LECROY-TRACE-002: input trace size changed: {label}")
                            continue
                    identity_ok_entries += 1

        if openers and identity is None:
            if not_applicable:
                warnings.append(
                    "LECROY-TRACE-002: trace-opening code changed but no trace identity recorded "
                    f"(declared not applicable: {not_applicable})"
                )
            else:
                violations.append(
                    "LECROY-TRACE-002: trace-opening code changed without trace_identity evidence "
                    f"or trace_identity_not_applicable: {', '.join(openers)}"
                )

        return ValidatorResult(
            ok=not violations,
            rule_ids=self.rule_ids,
            violations=violations,
            warnings=warnings,
            evidence_summary=(
                f"captures={len(captures)} trace_openers={len(openers)} "
                f"identity_entries_preserved={identity_ok_entries}"
            ),
            metadata={
                "mode": "hard_stop_via_contract",
                "captures": captures,
                "trace_openers": openers,
            },
        )
