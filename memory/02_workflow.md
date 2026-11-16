# Tech Stack

## Repo Facts

- Fill in runtime, language, and tooling facts for this repo.

## Architecture Decisions

- 2026-11-16 G1: AI Governance is consumed as the `ai-governance-framework`
  submodule (pinned 6c7e24c3) and updated only through
  `governance_tools.f7_full_update`. Supersedes the G0 copy-based minimal audit.
  Scope, open items and acceptance criteria: PLAN.md "G1 governance full adoption
  decision".
- 2026-11-16 G1-3: domain validators live in `governance/validators/` with rule
  pack `governance/rules/lecroy`; LECROY-TRACE-001/002 are contract hard stops,
  LECROY-DEL-001 is advisory. L2 escalation is declared in AGENTS.md because the
  framework detector has no LeCroy keywords.
