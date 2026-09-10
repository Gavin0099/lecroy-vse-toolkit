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
| M2 | Packet extraction | Not started; next product slice | Replayed packet output with fields verified against the LeCroy view. |
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
functionally PASS; the next gate is the consumer-owned G0 topology decision.

## G0 governance adoption boundary

G0 starts only after M1 has a real-trace PASS. It is intentionally separate from the VSE feasibility experiment so a failure can be attributed to the correct layer.

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

When G0 is authorized, use a clean checkout or worktree derived from the GitHub source, record its exact commit SHA, run `adopt_governance.py --dry-run`, review the predicted files, and only then apply adoption. Do not use the current dirty local framework checkout as the source baseline.

G0 adoption artifacts do not by themselves prove runtime governance, hook
execution, fail-closed behavior, or memory continuity. Those require separate
runtime evidence. Do not turn those evidence gaps into implementation work
until the consumer-owned topology decision justifies that cost.
