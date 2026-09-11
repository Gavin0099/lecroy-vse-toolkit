# Plan

## Objective

Verify that LeCroy USB Protocol Suite VSE can read a large USB trace, expose useful decoded events, and deliver machine-readable data to a host that can support bounded diagnostic triage.

The repository name remains `lecroy-vse-toolkit` because that is the existing checkout and remote identity. The working posture is experimental/lab; no product or analyzer claim is implied.

## Milestones

| ID | Milestone | Status | Exit evidence |
| --- | --- | --- | --- |
| M0 | Repository bootstrap | Ready | Repo structure, scope, reference policy, and fixture policy exist. |
| M1 | Minimal VSE execution and host-owned summary bridge | PASS; historical anomaly recorded | A real `.usb` trace completes the selected VSE traversal, sends the required summary once through `NotifyClient()`, and the host produces a verifiable artifact with controlled integrity qualification. |
| G0 | Governance topology decision | Decision recorded: Minimal Audit + Lightweight Memory | The consumer decision is recorded from the Before/After evidence; runtime capability remains explicitly bounded. |
| G0-C1 | State authority correction | Controlled fresh-context behavior PASS; delivery tracked in Git | Memory alone did not reopen PASS in one isolated sub-agent case; not a universal recovery claim. |
| M2 | Packet extraction | M2-PACKET-EXTRACTION-1 through M2-PACKET-EXTRACTION-3 PASS; broader coverage not complete | Bounded selected decoded events cross VSE -> COM -> Host with event identity, selected protocol fields, JSON read-back, and controlled trace integrity. |
| M2-4 / DEMO-1 | Unified timeline and PASS vs FAIL candidate comparison | QUALIFIED for controlled source-preserving read-only mode | One combined extractor produces normalized timelines for PASS/FAIL candidates, reports a common-anchor candidate divergence without claiming absolute first divergence, and preserves the immutable source artifact. |
| DEMO-2 | One-click PASS/FAIL runner | Implemented; integrity closure PASS; Windows PowerShell 5.1 compatibility PASS | One command creates read-only sandbox copies, runs both extractions, compares timelines, verifies source and working-copy integrity, and writes JSON plus Markdown artifacts. |
| DEMO-C2 | Reliable common-anchor gate | PASS for fail-closed behavior on the known pair | Weak or insufficiently contextualized anchors are rejected; `NO_RELIABLE_COMMON_ANCHOR` produces no GUI recommendation. |
| DEMO-C3 | Timestamp fidelity | PASS | VSE seconds/nanoseconds survive the VSE -> COM -> Host -> JSON path with 0 ns error for the expert-labeled FAIL timestamp; comparator logic is unchanged. |
| DEMO-C4 | Semantic alignment | PASS for fail-closed behavior; useful alignment not proven | A verified raw-field and relative-gap fingerprint is unique in FAIL but has no PASS match, so `NO_RELIABLE_SEMANTIC_MATCH` is emitted and no GUI handoff is produced. |
| DEMO-C5 | Automatic suspicious-region discovery | PASS for the known pair; generalization not proven | Without a ground-truth input, PASS baseline scoring ranks a FAIL window intersecting the expert-labeled region at Top 1; the result remains triage evidence only. |
| DEMO-V1 | Engineer HTML report | PASS for presentation layer | Existing C5 JSON is rendered as a single offline HTML report with Top-3 candidates, exact timestamps, reasons/features, PASS/FAIL overview, integrity, and claim boundary. The JSON remains canonical; scoring is unchanged. |
| DEMO-V2 | Engineer-first triage report | PASS for presentation layer | Adjacent C5 windows are grouped into suspicious episodes; the report foregrounds the actionable interval, quantitative PASS baseline comparison, and claim boundary while retaining JSON as canonical. C5 scoring is unchanged. |
| DEMO-V3 | Evidence timeline | PASS for presentation layer on the known pair | Existing timeline events are visualized at their actual positions inside the primary episode; trace basenames are shown and exact internal metadata remains in details. Missing event-position data fails closed to a clear fallback message. |
| DEMO-V4 | Plain-language triage summary | PASS for presentation layer on the known pair | The Hero adds a conservative observation summary; selected LTSSM timestamps are labelled; secondary candidate scores stay in details; raw LFPS duration and baseline direction are easier to scan. C5 JSON and scoring are unchanged. |
| DEMO-V5 | Instrument color semantics | PASS for presentation layer on the known pair | Graphite surfaces, instrument blue, investigation amber, and integrity green now have distinct meanings; LFPS, LTSSM, and LINK_CMD use separate timeline colors. Layout, C5 JSON, and scoring are unchanged. |
| DEMO-V6 | Plain-language report copy | PASS for presentation layer on the known pair | The first screen leads with plain-language findings and next action; protocol names remain as secondary labels; p95, ranking details, and technical limits stay in expandable details. C5 JSON and scoring are unchanged. |
| DEMO-V7 | Capability/method/limit copy | PASS for presentation layer on the known pair | The report separates what the tool can do, how it works, and what it cannot claim; the Hero uses direct LFPS wording and secondary candidate ranking data stays hidden by default. C5 JSON and scoring are unchanged. |
| M3 | Transfer reconstruction | Not started | Control/bulk/interrupt/isochronous transfer grouping replayed and checked. |
| M4 | Enumeration analyzer | Not started | Reset-to-configuration sequence checks with bounded findings. |
| M5 | Large-trace performance validation | Not started | Trace size, event count, runtime, peak memory, and output size recorded. |
| M6 | Automation API integration | Not started | Repeatable open-trace/run-VSE/collect-result flow. |
| M7 | AI-assisted diagnosis | Not started | Optional explanation over normalized deterministic evidence. |

## Architecture decision: M1-B host-owned artifacts

The product requirement is an external, verifiable analysis result. It does
not require the VSE script itself to own Windows filesystem output. The
selected M1 architecture is:

```text
.usb trace
    -> LeCroy decoder/VSE
    -> deterministic event counters and findings
    -> NotifyClient()
    -> Automation host
    -> summary.json / summary.md / later triage artifacts
```

The earlier VSE-owned `OpenFile()` route remains recorded as a non-blocking
compatibility investigation. Its physical filesystem effect was not observed
in the local 10.40 Automation context, but that does not block the host-owned
route.

`M1-COM1` proved a bounded first-event VSE-to-host bridge. `M1-COM2` proved
that the known full-trace counters can cross that bridge once and match the
existing `trace-info.vse` baseline. `M1-COM3` added only host-side JSON
serialization and passed the artifact write/read-back acceptance. The run also
exposed an unexplained change to the input trace file, so the repository cannot
yet be declared a clean baseline. `M1-I1` repeated the relevant open/close,
VSE, and separate-output combinations on sacrificial copies without
reproducing the mutation. `M1-I2` then repeated the exact same-folder COM3
layout on a fresh sacrificial copy and also preserved the input identity.
M1 is now functionally qualified; the historical discrepancy remains recorded
as `UNEXPLAINED / NOT REPRODUCED`.

## G0 governance topology decision

The Before/After experiment established that static audit adoption can add
baseline identity, a contract, claim/scope guidance, and drift/readiness
visibility without changing M1 product behavior. It did not establish runtime
governance value.

This slice is a consumer-repository adoption decision, not an
ai-governance-framework task.

### Decision

The consumer decision is:

yaml:
  static_audit_adoption: BENEFICIAL_WITH_COST
  full_governance_value: INCONCLUSIVE
  G0_RESULT: RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY
  runtime_governance: NOT_ADOPTED
  runtime_readiness: PARTIAL_BY_DESIGN
  automatic_memory: NOT_CLAIMED

This is a LeCroy repository adoption decision, not an
ai-governance-framework task.

### Lightweight project memory

Keep a small, manually maintained project memory with only:

- current_goal;
- current_status;
- important_decisions;
- verified;
- not_verified;
- known_issues;
- next_step.

For the current project, this records M1 PASS, the verified trace-to-JSON
evidence, the historical mutation as UNEXPLAINED / NOT REPRODUCED, and M2 as
the next product slice.

### Explicitly excluded

Do not add these capabilities as part of G0:

- automatic stop/session memory writes;
- closeout receipts;
- memory authority or promotion chains;
- record-identity hashing;
- pressure state machines;
- full hook enforcement;
- autonomous memory consolidation.

### Established evidence

- M1 BEFORE: PASS.
- M1 AFTER: PASS.
- Product regression: 0.
- Product code mutation during adoption: 0.
- Static audit surface: established.
- Drift/readiness gap detection: established.
- Limited fail-closed case: observed.
- Runtime governance, hooks, memory continuity, and independent verification:
  not proven.

### Decision rule and boundary

Choose Runtime-Capable Mode only if LeCroy has a concrete, observable runtime
failure that this capability would address at worthwhile cost. Do not select it
merely because readiness is false or because the copied audit surface is not
self-contained.

After this decision:

- M2 is the next separate product slice, but this update does not start it.
- Missing runtime, hook, memory, or version surfaces remain findings, not
  implementation tasks.
- No Governance framework files are changed.
- Automatic memory is not claimed.

The first VSE script is intentionally a probe, not a parser. It requests all channels and trace events, counts the events delivered to `ProcessEvent()`, records trace and callback time boundaries, and records coarse channel and level buckets. The selected architecture sends the machine-readable result to the host rather than requiring VSE-owned file output.

The M1 claim ceiling is:

- `SUPPORTED`: the repository contains VSE probes using the locally observed lifecycle, event-delivery, and `NotifyClient()` primitives.
- `PROVEN`: the known real `.usb` trace completed the COM2 traversal and delivered the required four counters once to the host.
- `PROVEN`: host-side JSON serialization and read-back verification for the known trace.
- `PROVEN`: I1 sacrificial-copy A/B/C runs preserved input hash, size, and UTC mtime.
- `QUALIFIED`: I2 exact same-folder COM3 reproduction preserved input hash, size, and UTC mtime.
- `RECORDED`: the original input `.usb` size/timestamp change remains `UNEXPLAINED / NOT REPRODUCED`.
- `UNKNOWN`: whether the delivered-event count equals all events in every trace/version/configuration.
- `OUT OF SCOPE`: packet schema completeness, transfer reconstruction, analyzer correctness, large-trace performance, automation, and AI diagnosis.

## Rules for advancing

1. Keep each milestone a separate, reviewable slice.
2. Consume fields already exposed by LeCroy; do not reimplement the LeCroy decoder.
3. Do not commit vendor samples or trace captures without an explicit license/handling decision.
4. Use a known trace and retain replayable observations for every runtime claim.
5. Do not add AI, RAG, agents, or plugin abstractions before deterministic extraction has passed a real replay.

## M1 runtime record

For the first successful run, record at least:

```yaml
trace: <external path or redacted identity>
application: Teledyne LeCroy USB Protocol Suite
application_version: <observed version>
script: scripts/hello/trace-info.vse
output: host-owned artifact path, or `NONE` for bridge-only probes
process_event_calls: <observed count>
script_result: <observed result>
runtime: <measured duration>
```

The COM2 record is in `scripts/io-probe/real-summary-notify-results.md`, the
COM3 record is in `scripts/io-probe/host-summary-json-results.md`, the I1
record is in `scripts/io-probe/trace-integrity-isolation-results.md`, and the
I2 record is in `scripts/io-probe/exact-com3-integrity-results.md`. M1 is
functionally PASS; M2-PACKET-EXTRACTION-1 and M2-PACKET-EXTRACTION-2 are now
complete bounded extraction slices.

## G0 governance adoption boundary

G0 was evaluated only after M1 had a real-trace PASS. It remains separate from
the VSE feasibility experiment so failures can be attributed to the correct
layer.

```yaml
canonical_source: https://github.com/Gavin0099/ai-governance-framework
product_baseline_commit: bd93629e6c5241cc42df76ac366d14c97157ac78
framework_commit: 77262a51d79c1c6a1b5eff55ce3f4a64f5af3f37
local_dirty_checkout: E:\BackUp\Git_EE\ai-governance-framework
adoption_status: STATIC_AUDIT_SURFACE_APPLIED
topology_decision: RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY
runtime_governance: NOT_ADOPTED
runtime_readiness: PARTIAL_BY_DESIGN
automatic_memory: NOT_CLAIMED
lightweight_memory: MANUAL_PROJECT_NOTES
```

The G0 experiment used a clean checkout derived from the GitHub source, pinned
the exact framework commit, reviewed the dry-run, and applied the adoption as a
separate commit. The dirty local framework checkout was not used.

G0 adoption artifacts do not by themselves prove runtime governance, hook
execution, fail-closed behavior, or memory continuity. Those require separate
runtime evidence. Do not turn those evidence gaps into implementation work
until the consumer-owned topology decision justifies that cost.

## M2-PACKET-EXTRACTION-1 result

The first M2 slice extracts only the installed LeCroy decoded event
_USB3_LINK_CMD from _USB3_TX and _USB3_RX. It exports event index, timestamp
text, and event type through the existing VSE -> COM -> Host path.

The batched transport result is recorded in
scripts/m2-packet-extraction-1-results.md. This slice does not claim complete
packet extraction, suspicious regions, root cause, comparison, GUI guidance,
or AI explanation.

## M2-PACKET-EXTRACTION-2 result

The second M2 slice extracts the installed LeCroy decoded event
_USB3_LTSSM_STATE. It exports event index, timestamp text, and event type
through the existing batched VSE -> COM -> Host path. The state name is not
exported because no reliable decoded state field was established for the
installed 10.40 environment; no state mapping is inferred.

The execution record is in
scripts/m2-packet-extraction-2-results.md. It records 30 target events,
matching Host reconstruction, JSON read-back, and unchanged sacrificial trace
integrity. M2 now has two completed post-G0 product slices; the third slice is
recorded below.

## M2-PACKET-EXTRACTION-3 result

The third M2 slice extracts the installed LeCroy decoded event _USB3_LFPS.
It exports event identity plus the LFPS-specific input context members Type,
Duration, DurationSec, DurationNS, PatternType, and StartsPattern through the
existing batched VSE -> COM -> Host path. The values remain raw numeric
observations; no LFPS type or pattern name mapping is inferred.

The execution record is in
scripts/m2-packet-extraction-3-results.md. It records 47,006 target events,
complete Host reconstruction, JSON read-back, and unchanged sacrificial trace
integrity. The three-slice product threshold is now met. Governance
retrospective eligibility still depends on the separately defined meaningful
interaction threshold; no retrospective is started by this product slice.

## M2-4 / DEMO-1 result

The combined extractor and PASS vs FAIL comparator are recorded in
docs/demo-1-pass-fail-results.md. Both candidate timelines were produced with
one shared extractor and complete Host reconstruction. The comparator found a
common sequence anchor and emitted candidate GUI windows without comparing
absolute timestamps or claiming root cause.

The FAIL working copy preserved input identity. The initial PASS working copy
grew by 20 bytes during VSE execution, including when restored from the
pristine Desktop zip. DEMO-I1 localized that mutation to 307 changed byte
positions across 15 ranges, including existing content and an appended
20-byte tail.

`DEMO-I2` then used the preserved pristine source artifact as an immutable
source, created a separate working copy, set the working copy read-only, and
ran the same combined extractor. The source SHA-256 remained unchanged, the
read-only working copy completed successfully, and the working copy also
remained unchanged for this run. DEMO-1 is therefore qualified for this
controlled source-preserving read-only mode. The earlier mutation remains a
known anomaly; the qualification does not claim that every trace, version, or
execution context is universally immutable.

## DEMO-2 one-click runner

`run-demo.ps1` packages the qualified Demo workflow behind one command. It
refuses to overwrite an existing output directory, records source SHA-256 and
size before and after, creates separate read-only sandbox copies, runs the
same combined extractor for both traces, and writes:

```text
pass-timeline.json
fail-timeline.json
comparison.json
source-integrity.json
report.md
sandbox/pass/<trace>.usb
sandbox/fail/<trace>.usb
logs/
```

The runner treats source evidence integrity as the hard safety gate. A missing
common anchor is reported in `comparison.json` and `report.md`; it is not
silently converted into a root-cause or PASS/FAIL claim.

`DEMO-2-WINPS-COMPAT` ran the exact repository-relative inputs in a fresh
Windows PowerShell 5.1 process. Add-Type, script parsing, existing-output
refusal, full extraction, comparison, and source-integrity acceptance all
passed. The Windows PowerShell comparator's higher resource cost remains an
observation for M5, not a correctness failure.

## DEMO-2 integrity closure

The runner now records SHA-256, size, UTC mtime, and read-only state for both
source traces and both disposable working copies. The run fails before
comparison when any source changes, either working copy changes, or either
working copy loses its read-only state. The Windows PowerShell 5.1
qualification harness asserts the same working-copy evidence in the emitted
`source-integrity.json`.

The controlled closure run is recorded in
`docs/demo-2-integrity-closure-results.md`. It passed on the known local
PASS/FAIL pair with source evidence integrity, working-copy integrity, and
the combined `analysis_input_integrity` all true. This closes the current
working-copy integrity hold for the selected source-preserving runner mode;
it does not claim universal immutability across traces, LeCroy versions,
Windows policies, or execution contexts.

## G0-C1 state authority correction

The natural fresh-session observation exposed a Lightweight consumer defect:
stale `memory/01_active_task.md` could steer task judgment toward an already
closed DEMO-1 hold even though the newer PLAN/evidence state qualified the
controlled source-preserving mode. The active-task file is a derived handoff,
not an independent authority.

The bounded C1 correction is recorded in the repo-local `AGENTS.md` rule and
the report-only `tools/test-state-authority.ps1` probe. On a conflict, the
consumer must emit `memory_state_conflict`, use current user instruction plus
verified evidence/PLAN for the product decision, and preserve the dirty memory
file for explicit reconciliation.

`FULL_VS_LIGHT_PILOT` is deferred. No Governance clone, runtime hook, writer,
validator, or framework file is added by C1. Product M3 resumes only after
this C1 rule passes the scoped fresh-session behavioral check and review.

The C1 result is recorded in
`docs/g0-c1-state-authority-results.md`. The script checks rule text only;
it does not prove Agent behavior. One separate fresh-context sub-agent case
passed on 2026-09-11; review and delivery are recorded with the scoped Git change. This controlled observation
does not establish universal natural-session recovery.
