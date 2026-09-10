# AI Governance Before / After Controlled Adoption Experiment

Date: 2026-09-10
Repository: `lecroy-vse-toolkit`
Product baseline: `bd93629e6c5241cc42df76ac366d14c97157ac78`
Framework source: `https://github.com/Gavin0099/ai-governance-framework`
Framework commit: `77262a51d79c1c6a1b5eff55ce3f4a64f5af3f37`
Known trace: `dp1 hub detect SSD fail-2.usb`

## Decision

`STATIC_AUDIT_ADOPTION = BENEFICIAL_WITH_COST`

`FULL_GOVERNANCE_VALUE = INCONCLUSIVE`

`G0_RESULT = RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY`

`runtime_governance = NOT_ADOPTED`

`runtime_readiness = PARTIAL_BY_DESIGN`

`automatic_memory = NOT_CLAIMED`

The canonical installer produced a copy-based audit surface with a contract,
protected baseline metadata, repository instructions, memory scaffolds, and a
drift checker. This establishes useful static auditability without proving the
value of full runtime governance. Hooks were not installed, runtime capability
was not established, and the runtime smoke path was blocked by missing version
metadata.

The selected LeCroy topology keeps a small manually maintained project memory
for current goal, status, decisions, verified and unverified evidence, known
issues, and next step. It deliberately excludes automatic closeout, memory
authority, promotion chains, record-identity hashing, pressure state machines,
and autonomous memory consolidation.

The product result is unchanged: M1 remains PASS and M2 remains NOT STARTED.

## Scope and controls

The experiment froze the M1 product baseline and did not add packet extraction,
triage, GUI/report work, AI analysis, or unrelated cleanup. The local dirty
checkout at `E:\BackUp\Git_EE\ai-governance-framework` was not used. The
canonical framework was obtained from GitHub and pinned to the commit above.

The only installer used was the canonical
`governance_tools/adopt_governance.py`, first with `--dry-run` and then with
the apply command. No hand-copy simulation was used.

## BEFORE / AFTER functional matrix

| Capability | BEFORE | AFTER | Interpretation |
| --- | --- | --- | --- |
| M1 VSE traversal | PASS | PASS | Same real-trace workflow completed. |
| `NotifyClient()` bridge | PASS | PASS | One host callback with the same payload. |
| Host-owned JSON artifact | PASS | PASS | Write and read-back both succeeded. |
| Counters | `3186175 / 632512 / 2553662 / 1` | Same | No statistic drift observed. |
| Trace integrity on controlled copies | PASS | PASS | Hash, size, and UTC mtime unchanged. |
| Build manifest | NA | NA | No build system was introduced. |
| Existing test framework | NA | NA | No new test framework was introduced. |
| M2 functionality | NOT STARTED | NOT STARTED | Scope boundary preserved. |

The four counters are, in order: event count, USB3 RX, USB3 TX, and USB CC.
The historical mutation of the original trace remains recorded as
`UNEXPLAINED / NOT REPRODUCED`; it was not reproduced by the controlled I1 or
I2 runs.

## Adoption mutation inventory

The canonical apply added 66 files and modified one existing file:

| Surface | Count / result |
| --- | ---: |
| `.github/workflows/governance-drift.yml` | 1 |
| `.governance/` baseline surface | 1 |
| `.governance-payload-config.yaml` | 1 |
| `AGENTS.base.md`, `AGENTS.md`, `contract.yaml` | 3 |
| `governance/` documents and rules | 56 |
| `memory/` scaffolds | 4 |
| Existing `.gitignore` | modified; managed hygiene block added |
| Product M1 files changed | 0 |
| Active Git hooks installed | 0 |
| Validators declared | 0 |

The installer dry-run predicted the same governance-only topology. No `.usb`
trace or generated `summary.json` entered the repository.

## Governance capability matrix

| Capability | Result | Evidence boundary |
| --- | --- | --- |
| Scope / mutation control | VERIFIED, bounded | Dry-run and post-apply inventory showed no M1 product changes. |
| Repository baseline identity | PARTIAL | `.governance/baseline.yaml` records the product baseline and external framework path; no repository lock/adopted release was present. |
| Claim ceiling | PARTIAL | Generated instructions and reports state copy-based limits; runtime consumption was not independently verified. |
| Fail-closed behavior | VERIFIED, limited | Direct `pre_task_check.py` returned exit code 1 because `PLAN.md` freshness was `ERROR`. This proves a bounded refusal in that condition, not general enforcement. |
| Runtime self-containment | NOT PROVEN | `adoption_doctor` reported `copy_based`, `self_contained=no`, and `runtime_capable=not_checked`. |
| Hook / CI enforcement | NOT INSTALLED | No pre-commit or pre-push hook was added. One governance drift workflow was added, but workflow execution was not claimed. |
| Memory continuity | NOT VERIFIED | Four memory files were scaffolded; no cross-session restore or automatic closeout was proven. |
| Independent verification | NOT VERIFIED | The experiment was executed by one operator/agent; no independent reviewer replayed it. |
| Readiness | NOT READY | `external_repo_readiness.py` returned `ready=false`. |
| Governance drift | NOT PASS | `governance_drift_checker.py` returned `ok=false`, severity `critical`, with the single finding `plan_freshness`. |

The canonical adoption command itself exited zero, but that is not treated as
a complete adoption claim because the post-adoption drift and readiness checks
were not green.

The framework's human-readable adoption summary was emitted during the apply
run but rendered with broken Windows terminal encoding. The table above is a
reconstruction from machine-readable results, not a verbatim relay of that
summary.

## Runtime smoke result

The report-only doctor observed:

- adoption class: `copy_based`
- self-contained: `no`
- runtime capable: `not_checked`
- external framework dependency: observed
- root-level runtime hooks: absent

The quickstart smoke entered `controlled_refusal` because the target had no
`.governance/version_manifest.yaml`; it must not be described as a passed
runtime smoke. The direct low-risk pre-task probe also refused with a non-zero
exit code because the existing `PLAN.md` did not contain the required freshness
metadata.

## Cost and friction

- Adoption footprint: 66 new files, one modified `.gitignore`, and one added
  drift workflow.
- Product code footprint: zero files changed.
- Mandatory hook friction: none observed because hooks were not installed.
- Governance-only work: canonical source lookup/clone, dry-run, apply, doctor,
  readiness, drift, quickstart, runtime-surface, and direct pre-task checks.
- False blockers: none classified. The stale-plan and missing-version findings
  are real adoption gaps, even though they are not M1 product defects.
- Maintenance cost: medium to high for this small lab repository if the full
  copied document/rule surface is retained without a runtime-capable adoption
  decision.

## New capabilities and non-capabilities

New, bounded capabilities are:

1. A machine-checkable governance baseline tied to the product baseline commit.
2. A repo-local contract and protected-file inventory.
3. A copy-based instruction/rule/memory audit surface.
4. A repeatable drift/readiness report that exposes missing adoption surfaces.

Not established by this experiment:

- full runtime governance;
- installed hook enforcement;
- independent verification;
- automatic memory continuity;
- framework lock freshness or a recorded adopted release;
- domain correctness or M1 semantic correctness beyond the existing M1 evidence.

## Final assessment

The adoption added useful static auditability and did not regress the
trace-to-JSON pipeline, so the static surface is beneficial with a measurable
cost. The value of full runtime governance remains inconclusive by design. The
`plan_freshness` finding and missing runtime/version surfaces remain adoption
findings, not reasons to expand Governance implementation.

## One next slice

`M2-PACKET-EXTRACTION`: start the next independent product slice for
deterministic packet extraction on the known trace. Maintain the lightweight
project memory manually while working on M2. Do not expand Governance runtime
capabilities as part of M2.
