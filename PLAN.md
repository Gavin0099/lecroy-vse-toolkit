# Plan

## Objective

Verify that LeCroy USB Protocol Suite VSE can read a large USB trace, expose useful decoded events, and deliver machine-readable data to a host that can support bounded diagnostic triage.

The repository name remains `lecroy-vse-toolkit` because that is the existing checkout and remote identity. The working posture is experimental/lab; no product or analyzer claim is implied.

## PCIe feasibility scope (revised 2026-09-12)

The owner adopted same-repository USB/PCIe work with isolated implementations.
Existing USB results retain their original scope. No common core is established.
P0-A setup baseline is accepted. The owner's latest instruction authorizes
sequential execution: verify each slice separately, then proceed on PASS
without repeated confirmation. FAIL/BLOCKED or a required scope decision stops
the sequence; this does not combine B1, B2 and B3 into one acceptance claim.
The owner's subsequent staircase instruction replaces the C1-only retry stop:
close each evidence gate in order, proceed on PASS without reconfirmation,
and stop on FAIL/BLOCKED or a required owner decision. No speculative later
implementation, presumed three-class event set or automatic C5 reuse follows.
The latest diagnosis-first V1 roadmap supersedes prior D2/E ordering and IDs:
D1e → E1a ground truth → E1b diagnostic question → D2c/D2d/(D2e)/D2f
signal sufficiency and model freeze → E2a-E2d minimal triage → E3a-E3e testing
→ F1 structured findings → F2 Markdown / F3 HTML → F4 UX alignment
→ F5 Engineer Review Build.
B1-B4 and C1a-D1d are not reopened. Each slice is validated before advancement;
E3 is the final integrated test series, not permission to postpone all checks.
From D1e through the E3e analysis gate there are 14 required slices and two conditional slices: D2e adds only
one signal if evidence proves TLP insufficient; E3d may defer if no second
ground-truth pair is available. Unknown ground truth is not a technical D1e
prerequisite, but it cannot be guessed to bypass E1a.
Analysis V1 is established only at E3e; the engineer-evaluable MD/HTML first
release additionally requires F1-F5. These are distinct delivery gates.
The earlier E4a report/UX proposal is replaced by F1-F5, not a parallel task.
Broader multi-trace coverage and automation/host work remain outside this
review-build path; no COM/host implementation follows without observed need.
The prior USB independent-pair validation remains a
separate pending task, not a PCIe prerequisite or a reopened USB milestone.

| Slice | Scope | State |
| --- | --- | --- |
| PCIe-P0-A | Setup baseline and external sample provenance | PASS for setup inventory (2026-09-12): installed PETracer.exe 13.26 Build 43 BETA and VSE files/location verified; September 11 sample provenance and integrity policy retained. Trace compatibility and script execution remain UNKNOWN. PCIe-P0 is not PASS. |
| PCIe-P0-B1 | Trace Open Baseline | PASS (2026-09-12): exact candidate copy loaded, Ready and navigable packet content; post-close integrity unchanged. |
| PCIe-P0-B2 | VSE Entry Discovery | PASS: actual Tools → Run verification scripts dialog/list observed before any script run. |
| PCIe-P0-B3 | Vendor Sample Execution | PASS: unchanged examp_tlps.pevs produced output and DONE on the selected trace. |
| PCIe-P0-B4 | Minimal Execution Evidence | PASS: B1-B3 reproduced on a fresh protected copy; identities and GUI evidence retained. |
| PCIe-P0-C1a | Channel Bootstrap | PASS for the narrow channel diagnostic: SendAllChannels removed it; historical overall C1 attempt remained FAIL with no events. |
| PCIe-P0-C1b | Event Bootstrap | PASS: vendor-backed TLP subscription removed event error; fixed marker, DONE, no new runtime error. |
| PCIe-P0-C1c | Clean Minimal Execution | PASS: separate fixed-message run, normal end and zero observed runtime errors; no trace-field reads. |
| PCIe-P0-C1d | Reproducibility | PASS: fresh read-only copy and reopened VSE reproduce clean execution; post-close integrity unchanged. C1 own-script execution PASS, not extraction. |
| PCIe-P0-C2a | Primitive Inventory | PASS: actual prior vendor output mapped to installed helpers; bounded inventory in staircase evidence, no extractor. |
| PCIe-P0-C2b | One Primitive Read | PASS: own script read vendor in.Index=1944516. |
| PCIe-P0-C2c | Primitive Reproducibility | PASS: separate same-trace execution returned 1944516 again. |
| PCIe-P0-C2d | Trace Dependency Proof | PASS: skipping the first callback changed the read to 1944517; no runtime error. |
| PCIe-P0-D1a | Candidate Event Inventory | PASS for bounded candidate inventory: TLP with observed metadata; triage usefulness remains a hypothesis, no scorer. |
| PCIe-P0-D1b | Single Event Extractor | PASS for bounded spike: first five TLP records reproduced in two runs; no full-trace coverage claim. |
| PCIe-P0-D1c | Extraction Contract | PASS for D1 projection-v1 only: field/unit/identity and cap documented in staircase evidence; not the final triage model or shared schema. |
| PCIe-P0-D1d | Cross-check | PASS for five-record projection: exact GUI packet references/families/widths and coarse time agree; vendor subtype references documented. No full-trace or physical-channel claim. |
| PCIe-P0-D1e | Cross-trace Extraction | PASS (2026-09-12): existing B output matched five actual GUI TLPs; trace closed and A/B source plus B copy hashes unchanged. Same extractor on two distinct files; first-five projection only, no ground-truth or full-coverage claim. |
| PCIe-P0-E1a | Ground-truth Pair Qualification | BLOCKED on ground truth: trustworthy PASS/FAIL provenance, test operation and observed behavior. Does not block technical D1e. |
| PCIe-P0-E1b | Diagnostic Question Freeze | NOT STARTED; fix one operation → normal expectation → FAIL symptom → question for triage, after E1a. |
| PCIe-P0-D2c | Candidate Signal Model | NOT STARTED; derive candidate PCIe signals from the qualified diagnostic question, not API availability. No scorer design. |
| PCIe-P0-D2d | TLP Sufficiency Test | NOT STARTED; test whether existing TLP extraction supplies observable evidence relevant to that question on the qualified pair. Current cap/display time do not establish full counts or precise timing. |
| PCIe-P0-D2e | Additional Signal Spike | CONDITIONAL / NOT STARTED; add only one justified signal if D2d establishes a gap; DROP if TLP is sufficient. Historical extra-class DROP does not prejudge this new test. |
| PCIe-P0-D2f | V1 Event Model Freeze | NOT STARTED; after E1a/E1b and sufficiency evidence, fix signals, PCIe-only schema and necessary/excluded fields. No triage implementation before freeze. |
| PCIe-P0-E2a | Raw PASS/FAIL Divergence | NOT STARTED; reproducible count/timing/sequence differences within validated extraction coverage and units, without scores or heuristics. |
| PCIe-P0-E2b | First Meaningful Divergence | NOT STARTED; at least one difference relevant to the failure symptom and explainable from GUI/trace, not metric proliferation. |
| PCIe-P0-E2c | Normalized Evidence Contract | NOT STARTED; minimal PCIe triage-consumable evidence contract, not USB/PCIe canonical schema or report UX. No assumed USB scorer reuse. |
| PCIe-P0-E2d | Minimal Triage Runner | NOT STARTED; one defined extraction → comparison flow on the two traces, no AI ranking or assumed host requirement. |
| PCIe-P0-E3a | First End-to-end PASS/FAIL Test | NOT STARTED; real qualified pair through the whole pipeline; different scores alone are insufficient. |
| PCIe-P0-E3b | Explanation Cross-check | NOT STARTED; findings trace back to GUI/packet/timestamp evidence, not black-box scores. |
| PCIe-P0-E3c | Repeatability | NOT STARTED; same pair reproduces findings/anchors/evidence; no all-trace or cross-version claim. |
| PCIe-P0-E3d | Second-pair Sanity Check | CONDITIONAL / NOT STARTED; second known pair checks overfit, DEFER permitted if unavailable. |
| PCIe-P0-E3e | PCIe V1 Testable Gate | NOT STARTED; at least one real qualified pair produces stable, credible, traceable analysis. Not a production/full-coverage claim. |
| PCIe-P0-F1 | Finding Contract | NOT STARTED; after E3e, establish PCIe analysis structured findings as the authoritative report input (analysis.json or equivalent). This is not a USB/PCIe canonical extraction schema. |
| PCIe-P0-F2 | Markdown Report | NOT STARTED; automatically render inputs, symptom, candidates, evidence and limitations from F1 findings in engineer-readable language. No independent analysis in the renderer. |
| PCIe-P0-F3 | HTML Report | NOT STARTED; render the same F1 findings as HTML, preserving findings/evidence/limitations shared with Markdown. No trace reanalysis or different verdicts. |
| PCIe-P0-F4 | USB / PCIe UX Alignment | NOT STARTED; align report structure, cards, PASS/FAIL comparison and evidence navigation only. Do not share or equate diagnostic semantics, event classes or scorers. |
| PCIe-P0-F5 | Engineer Review Build | NOT STARTED; one qualified real case plus structured findings, generated MD/HTML and evidence traceable back to LeCroy. This prepares the first engineer evaluation; it does not establish positive feedback or measured time savings. |

Prior D2 optional-class DROP/SKIP decisions remain historical: no extra class
was implemented, and old statuses do not complete newly defined slices.
Model freeze is now D2f and explicitly follows E1a/E1b. E1a establishes labels
and observations, E1b fixes one use case, and only then can D2 determine signal
necessity. The candidate TLP projection is not the final diagnostic model.

This revision replaces the earlier B=event/GUI correlation, C=programmatic
execution, D=completion/counts/JSON, and E=qualification-only roadmap. Old
references to those letters are historical, not current execution instructions.
The former F abstraction candidate remains deferred outside this sequence;
the new F1-F5 reporting slices do not revive shared-core architecture work.

### Engineer-review delivery boundary

E2c defines the minimum PCIe analysis evidence consumed by the triage flow.
F1 subsequently fixes the structured finding output consumed by both report
renderers. "Canonical" at F1 means the authoritative PCIe report input only;
it does not formalize a shared USB/PCIe event schema. Exact fields are decided
at their gated slices, not implemented by this roadmap update.

F5's intended local delivery is one qualified PASS/FAIL case with
`analysis.json` (or equivalent structured findings), `report.md`, `report.html`
and enough input/packet/time/context identity to return to the original LeCroy
evidence. MD and HTML must reflect the same analysis result. The existing
source-preserving trace policy remains: captures stay outside Git, referenced
by verified identities or supplied as appropriately authorized separate copies.
Do not relabel the current unknown-outcome A/B captures as PASS/FAIL to create
this package. No report or review build exists merely because these filenames
are specified here.

Engineer review should assess whether the suggested regions are worth looking
at, whether they actually reduce manual search effort, and which missing PCIe
evidence would improve usefulness. Those benefits require review evidence;
F5 readiness does not itself prove them. Better signals, heuristics, ranking
and candidate root-cause inference belong to a later V2 decision after useful
engineer feedback, not this V1 implementation path.

Evidence and missing inputs: [PCIe setup](docs/setup/pcie-protocol-suite.md),
[runtime evidence](docs/pcie-runtime-baseline.md),
[staircase evidence](docs/pcie-staircase-evidence.md) and
[sample policy](samples/pcie/README.md). P0-A PASS is limited to installed
inventory. The historical hello-events.pevs draft remains unexecuted and is not
runtime evidence or the C1 implementation. No host or formal event schema is
adopted. Installer/package `25.28.43-BETA` and installed executable
`13.26 (Build 43)` BETA remain separate observed identities; their relationship
is UNKNOWN.

Current work: D1e complete; P1 manifest, P2 status matrix and P3 engineer handoff prepared in [handoff](docs/pcie-engineer-handoff.md). P4 is DEFERRED / LEGACY_FORMAT_COMPATIBILITY and does not block E1a: one trace showed a verified v12.36 format-update prompt, a second open reached a modal with unrecorded cause, and four traces remain untried; no extractor ran on these attempts. Reopen a separate P4a only if E1a confirms a required PASS/FAIL trace is among the legacy-format inputs. Stop diagnostic implementation at E1a pending test background. C1a-C1d, C2a-C2d and D1a-D1d retain
their documented bounded PASS. Trace A is `S0-Remove SD7-1350.pex`; Trace B
is the distinct `S0-Remove SD7-1335.pex`, selected by convenient size from the
existing owner-authorized Kent inventory. Both outcome labels remain UNKNOWN.
Different path and hash establish distinct files, not statistical independence
or known capture/test conditions. No filename is promoted to ground truth.

### Independent single-trace inspection branch (F0)

This owner-authorized presentation branch uses already verified Trace A evidence
and proceeds independently of E1a. It does not establish a device verdict,
diagnostic usefulness, or full-trace coverage, and it does not move the E1a
ground-truth gate. The inspection observation schema is PCIe-only and local to
this report; it does not replace the later F1 finding contract or establish a
USB/PCIe schema. The retained preview is in
[`artifacts/reports/pcie-inspection-1350-20260912`](artifacts/reports/pcie-inspection-1350-20260912/report.md).

| Slice | Scope | State |
| --- | --- | --- |
| F0a | Single-trace structured observation contract | PASS: inspection-only schema; no PASS/FAIL or finding semantics. |
| F0b | Convert retained extractor output to structured data | PASS: verified VSE log, input identities and five GUI rows bind into `observations.json`; no new VSE execution or trace parsing. |
| F0c | Markdown inspection report | PASS: rendered from the saved structured JSON. |
| F0d | HTML inspection report | PASS: same JSON source, offline and script-free. |
| F0e | Single-trace UX review | READY_FOR_ENGINEER_REVIEW: local desktop render and claim boundaries checked; engineer feedback on usefulness/readability remains pending. |

This sample labels extraction `PASS_BOUNDED`, ground truth `UNKNOWN`,
diagnostic result `NOT_EVALUATED`, and coverage as the first five TLP records
only. Renderer mechanics may inform later work; F1 fields and diagnostic
semantics remain gated by E3e and their own evidence.

D1e is closed as PASS within the five-record projection: the unchanged
extractor produced TLP output for Trace B, five records were sampled against
the B trace GUI, the analyzer was closed, and source/working-copy identities
remained unchanged. The earlier GUI-focus interruption is retained as
historical evidence, not the current slice state. See the final D1e closure in
the [staircase evidence](docs/pcie-staircase-evidence.md) and [handoff](docs/pcie-engineer-handoff.md).

Continuation input check (2026-09-12): read-only `Get-ChildItem` confirmed the
eight GL9767 captures still have the recorded sizes. `rg --files` beneath the
owner-authorized `C:\Users\reiko\Desktop\Kent` tree found zero matching
companion files with extensions md/txt/csv/xlsx/xls/pdf/docx/log/json/html/png/jpg.
This is a bounded accessible-files search, not proof that no evidence exists
elsewhere. ZIP files and installer payloads were not opened. No source hash,
runtime execution or prior PASS was requalified by this metadata-only check.

Needed only at E1a: PASS trace, PASS observed behavior, FAIL trace, FAIL
observed behavior. Trigger/operation and expected behavior are useful context;
root cause is not required. These are not D1e prerequisites. A fixed D1
projection does not establish full-trace coverage, precision timing or the
necessary V1 event model. E1b+ and integrated V1 testing remain NOT STARTED.

### Slice acceptance and boundaries

Each slice has a distinct evidence record. A failed or inconclusive prerequisite
stops the sequence at that slice; an available later task is not a workaround.
Successful sample execution is a runtime-path result, not a PASS judgment about
the captured device. No blanket PCIe-P0 qualification follows from this table.

| Slice | PASS evidence | Explicit exclusion |
| --- | --- | --- |
| B1 Trace Open Baseline | The installed PETracer.exe accepts a known-source candidate working copy, completes loading to a usable state with visible/navigable packet/timeline/detail content, gives no incompatible/unsupported/corrupt rejection, and evidence identifies the exact input. | No VSE, packet analysis or extraction; file existence does not imply known-good. |
| B2 VSE Entry Discovery | With the B1 trace loaded, record an actual, repeatable GUI path to the VSE script execution dialog/list. | No script run, COM research or undocumented API guesses. |
| B3 Vendor Sample Execution | Run one unchanged installed vendor sample, such as examp_tlps.pevs, through B2's entry; observe and retain output, dialog, file or log evidence attributable to that run. A parse/runtime error is not success. | No vendor sample edits, own script, structured extraction implementation or host bridge. |
| B4 Minimal Execution Evidence | Record executable, source/copy, sample identities, exact B1-B3 steps and observations; repeat from a closed trace/new protected copy and reproduce loading, entry and sample execution a second time. | No automation or extraction implementation. |
| C1 Own Minimal Script | The staircase separately proves bootstrap, fixed message, normal termination with zero runtime errors, then fresh-copy repeatability. | No trace-field reads or event extraction; DONE with an error is FAIL. |
| C2 Read Trace Primitive | At least one vendor API trace/event value is observed with trace and script identity, distinguishing data access from C1's fixed message. | No complete data model or multi-class extraction. |
| D1 Extraction Spike | One selected PCIe event class is extracted with a checkable trace/event reference and field/unit meaning. | No three-class implementation or common schema. |
| D2 Extraction Expansion | Extend only to a PCIe event set justified by actual API/trace evidence; repeatable records preserve identity and field/unit meanings needed by the chosen analysis. | No report UX; USB event names alone do not establish PCIe equivalence. |
| E Integration | Real PCIe extraction feeds a specified analysis flow with validated input semantics and a replayable result. Existing USB scorer reuse requires evidence of compatible meanings. | No governance expansion, speculative architecture or automatic core/common-schema adoption. |

### P0-B1 — retained execution contract

Question: can the installed PCIe Protocol Suite open a known-source candidate
PCIe trace? This does not claim prior decoder compatibility, known-good data
or a verified PASS/FAIL capture label.

- Owner-authorized trace source root: `C:\Users\reiko\Desktop\Kent`.
  Input candidate: `ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`
  beneath that root, from the existing sample inventory. File existence and
  size (105,224,486 bytes) were checked during planning; this is not a trace-open
  result. It is the smallest candidate in that inventory;
  that is a selection convenience, not a correctness or quality judgment.
- Before opening: verify the selected source against its recorded identity;
  create a fresh external read-only working copy and record both paths,
  SHA-256, size, UTC mtime and attributes. Use the baseline's actual
  `PETracer.exe` path and record the executable identity for the run.
- Operation: open only that working copy in PETracer. Observe successful load
  and a usable trace view. Record elapsed loading time and an image or equally
  concrete observation binding the visible content to the selected file.
- PASS requires loaded trace content, responsive GUI, no format/version/corrupt
  rejection, and unchanged source/copy identity after closing the trace.
  Merely launching an application shell or seeing a filename is insufficient.
- FAIL: explicit open/format/version/corruption rejection, crash, or evidenced
  hang. Record the exact observed message/behavior. Do not infer incompatibility
  from a slow load alone. Loading still in progress or unavailable GUI evidence
  is inconclusive, not PASS; missing/mismatched input is a prerequisite blocker.
- If input integrity changes or read-only handling is rejected, stop and record
  it. Do not retry against the original or silently make the copy writable.
- UNKNOWN after B1: VSE GUI entry, vendor/own .pevs execution, extraction and
  COM necessity. These are not B1 acceptance requirements.
- Close the B1 evidence gate before any B2 work. Under the owner's subsequent
  continuation instruction, PASS proceeds to B2; FAIL/BLOCKED stops immediately.
  Do not debug the installer or investigate another implementation as a workaround.

### Deferred PCIe event and integration decisions

The proposed later `LINK_CMD / LTSSM_STATE / LFPS` set matches the current USB
extractor's `_USB3_LINK_CMD`, `_USB3_LTSSM_STATE` and `_USB3_LFPS` selections in
`scripts/m2-packet-extraction-4.vse`. The C5 scorer directly consumes these
classes in `tools/discover-c5-suspicious-regions.ps1`. This is repository
evidence of USB-specific behavior, not evidence of PCIe field equivalence.

Retain D1/D2/E as future goals. Their exact PCIe event set and integration
contract remain unresolved until C2/D1 supplies applicable evidence. Do not
rename PCIe data to satisfy the USB schema or manufacture absent event classes.
This dependency does not block earlier runtime gates. Investigate it only when
the applicable staircase prerequisites have passed, not as a fallback task.
COM/Automation and a minimal host remain conditional on an observed runtime need;
no current slice requires them simply because the package contains support.

## USB milestones

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
