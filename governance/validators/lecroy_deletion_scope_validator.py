#!/usr/bin/env python3
"""LeCroy deletion scope validator (rule LECROY-DEL-001, advisory).

Flags added deletion calls outside tests/ when checks.deletion_scope is missing.
Detection is a text match on added diff lines, so it is advisory and is not
listed in contract.yaml hard_stop_rules.
"""

from __future__ import annotations

import re

from governance_tools.validator_interface import DomainValidator, ValidatorResult

DELETION_PATTERNS = (
    re.compile(r"\bRemove-Item\b", re.IGNORECASE),
    re.compile(r"\brm\s+-[A-Za-z]*[rf]"),
    re.compile(r"\bshutil\.rmtree\s*\("),
    re.compile(r"\bos\.(remove|unlink|rmdir)\s*\("),
    re.compile(r"\.unlink\s*\("),
    re.compile(r"\b(File|Directory)\.Delete\s*\("),
    re.compile(r"\b(rmdir|rd)\s+/s\b", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fsq]\b", re.IGNORECASE),
)


def _added_lines_by_file(diff_text: str) -> list[tuple[str, str]]:
    current = ""
    added: list[tuple[str, str]] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = target[2:] if target.startswith("b/") else target
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append((current.replace("\\", "/"), line[1:]))
    return added


class LeCroyDeletionScopeValidator(DomainValidator):
    @property
    def rule_ids(self) -> list[str]:
        return ["lecroy", "LECROY-DEL-001"]

    def validate(self, payload: dict) -> ValidatorResult:
        checks = payload.get("checks") or {}
        diff_text = str(checks.get("diff_text") or "")
        scope = str(checks.get("deletion_scope") or "").strip()
        warnings: list[str] = []
        violations: list[str] = []

        if not diff_text:
            warnings.append("LECROY-DEL-001: no diff_text supplied; deletion scan skipped")
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                warnings=warnings,
                evidence_summary="deletion scan skipped (no diff_text)",
                metadata={"mode": "advisory", "matches": []},
            )

        matches = []
        for path, text in _added_lines_by_file(diff_text):
            if path.lower().startswith("tests/") or path == "/dev/null":
                continue
            if any(pattern.search(text) for pattern in DELETION_PATTERNS):
                matches.append({"file": path, "line": text.strip()[:160]})

        if matches and not scope:
            for match in matches:
                violations.append(
                    f"LECROY-DEL-001: added deletion call without deletion_scope: {match['file']}: {match['line']}"
                )

        return ValidatorResult(
            ok=not violations,
            rule_ids=self.rule_ids,
            violations=violations,
            warnings=warnings,
            evidence_summary=f"deletion_calls={len(matches)} scope_declared={bool(scope)}",
            metadata={"mode": "advisory", "matches": matches},
        )
