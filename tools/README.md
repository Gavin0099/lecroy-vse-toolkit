# Tools

run-m2-packet-extraction.ps1 is the M2-PACKET-EXTRACTION-1 host harness. It
reuses the M1 COM connection-point pattern, receives batched decoded
_USB3_LINK_CMD records from the VSE script, writes a host-owned packets JSON
artifact, reads it back, and verifies the sacrificial input trace hash, size,
and UTC mtime. It does not assign severity, suspicion, root cause, or AI
explanations.

run-m2-lfps-extraction.ps1 is the M2-PACKET-EXTRACTION-3 host harness. It
receives batched decoded _USB3_LFPS records, including the observed LFPS input
context fields, writes a host-owned JSON artifact, reads it back, and verifies
the sacrificial input trace hash, size, and UTC mtime. It retains raw numeric
field values and does not infer semantic enum names, severity, suspicion, root
cause, or AI explanations.

run-m2-timeline-extraction.ps1 is the combined M2-4 extractor. It emits the
three validated event classes in one traversal and verifies per-class counts,
raw VSE timestamp components, chronological event ordering, JSON read-back,
and trace integrity.

compare-m2-timelines.ps1 compares two normalized timeline JSON artifacts. It
uses stable event signatures, unique occurrence checks, and matching context
before and after the anchor. If no reliable common anchor is established, it
returns `NO_RELIABLE_COMMON_ANCHOR` and emits no GUI window. When an anchor is
accepted, it reports only a candidate divergence plus trace-local GUI windows;
it does not claim absolute first divergence, root cause, severity, or PASS/FAIL
classification.

compare-c4-semantic-timelines.ps1 is the C4 semantic-alignment probe. It uses
the expert-labeled FAIL region, verified LFPS raw fields, event context, and
relative timestamp gaps without using absolute cross-trace timestamps. It
returns `SEMANTIC_MATCH_FOUND`, `MULTIPLE_SEMANTIC_MATCHES`, or
`NO_RELIABLE_SEMANTIC_MATCH`; only a unique semantic match can emit a GUI
handoff. A no-match result is a valid fail-closed outcome, not a product
failure.

discover-c5-suspicious-regions.ps1 is the C5 triage probe. It builds a PASS
baseline from relative sliding windows, scans FAIL without a supplied failure
timestamp, and emits ranked inspection candidates. It does not claim root
cause, severity, automatic PASS/FAIL classification, or generalization from
one trace pair.

render-c5-html.ps1 is the DEMO-V1/DEMO-V2 presentation layer. It reads an
existing passing C5 JSON artifact and writes one offline Traditional Chinese
(`zh-Hant`) `report.html` with English protocol terms retained where useful.
DEMO-V2 groups adjacent candidate windows into suspicious episodes, moves the
actionable interval and claim boundary to the top, compares the episode with
the PASS p95 baseline, removes cross-signal bar charts, and collapses raw,
integrity, and technical evidence into details. DEMO-V3 additionally loads
the referenced FAIL timeline artifact and visualizes actual event positions
inside the primary episode; it does not invent positions when that artifact
is unavailable. None of these presentation versions changes C5 scoring, adds
a decoder, requires a network, or replaces JSON as the canonical artifact.

localize-trace-mutation.ps1 compares two binary trace files and reports changed
offset ranges plus bounded before/after hex. It localizes bytes only; it does
not assign semantic meaning or safety to the mutation.

The current DEMO-V4 presentation layer adds a conservative plain-language
observation summary, labels selected actual LTSSM timestamps in the evidence
timeline, keeps secondary candidate ranking scores behind details, identifies
the raw LFPS duration hint, and uses directional arrows in the local baseline
comparison. These are presentation-only changes; C5 JSON, scoring, and claim
boundaries are unchanged. The verified known-pair report is
`c5-output-20260911-v14/report.html`.

DEMO-V5 applies instrument-style semantic colors without changing the report
hierarchy: amber marks triage candidates and actions, blue marks information
and LFPS activity, amber marks LTSSM markers, muted gray-blue marks LINK_CMD,
and green is reserved for qualified source integrity. The verified known-pair
report is `c5-output-20260911-v15/report.html`.

DEMO-V6 applies a plain-language copy pass without changing the report layout
or analysis. The first screen explains the unusual behavior and recommended
GUI action in Traditional Chinese; LFPS, LTSSM, LINK_CMD, p95, ranking data,
and technical limits remain available as secondary details. The verified
known-pair report is `c5-output-20260911-v18/report.html`.

DEMO-V7 keeps that presentation layer deterministic and separates the visible
copy into tool capabilities, analysis method, and current limitations. The
Hero uses direct LFPS wording, while secondary candidate ranking scores stay
inside expandable technical details. C5 JSON and scoring remain unchanged.
The verified known-pair report is `c5-output-20260911-v20/report.html`.

run-m2-ltssm-extraction.ps1 is the M2-PACKET-EXTRACTION-2 host harness. It
receives batched decoded _USB3_LTSSM_STATE records, writes a host-owned LTSSM
event JSON artifact, reads it back, and verifies the sacrificial input trace
hash, size, and UTC mtime. It exports event index, timestamp, and event type;
it does not infer decoded state names, severity, suspicion, root cause, or AI
explanations.

`run-m1-com1-notify.ps1` is the bounded M1-COM1 host harness. It loads the
local C# COM connection-point sink, opens a trace through `CATC.UsbTracer`,
attaches to the VSE engine event interface, runs the script synchronously, and
prints the received `NotifyClient()` payload as JSON.

This is a capability probe, not the M6 automation wrapper. It does not write
summary files or claim end-to-end trace-analysis automation.

`run-m1-com2-notify.ps1` is the M1-COM2 host harness. It uses the same direct
Automation TypeLib connection-point approach, runs the full-trace summary
probe, and validates the single received payload against the known trace
baseline. It also prints the result as JSON, but intentionally does not write
the COM3 artifact yet.

`run-m1-com3-json.ps1` is the host-only COM3 wrapper. It reuses the COM2
bridge, refuses to overwrite an existing output, writes `summary.json` beside
the input trace, and reads the JSON back to verify all four fields. Its JSON
acceptance passed, but the associated execution record also documents an
unexplained input-trace mutation that must be resolved before a clean baseline.

The `m1-i1-*` tools are the sacrificial-copy integrity probes. I1-A tests only
Automation open/close, I1-B runs COM2 without JSON, and I1-C writes JSON to a
separate output directory before closing the trace. All three controlled runs
preserved their input copy; they do not prove universal immutability.

`M1-I2` uses a fresh copy and the exact COM3 same-folder output layout. It
passed the JSON and hash/size/mtime acceptance, so the M1 workflow is now
functionally qualified. The historical mutation remains an explicit
unexplained observation.

`DEMO-I2` uses a preserved pristine source artifact, creates a separate
read-only working copy, runs the combined M2-4 extractor, and verifies source
and working-copy SHA-256/size plus JSON read-back. The qualification target is
source evidence integrity; universal working-copy immutability is not claimed.

`run-demo.ps1` is the DEMO-2 wrapper. It applies the same source-preserving
read-only workflow to a PASS/FAIL pair, snapshots source and working-copy
SHA-256, size, UTC mtime, and read-only state before and after extraction,
and fails closed if the analysis inputs are not stable. It invokes both
timeline extractions, invokes the common-anchor comparator, and writes the
timeline, comparison, source-integrity, log, and Markdown report artifacts.
It refuses an existing output directory so prior evidence is not overwritten.

`m2-timeline-extraction.cs` intentionally uses legacy-compatible C# syntax and
reflection-based COM invocation because Windows PowerShell `Add-Type` may use
a compiler that does not accept newer language syntax or implicitly reference
`Microsoft.CSharp.RuntimeBinder`.

`test-demo2-winps-compat.ps1` is the exact-target qualification harness. It is
intended to be launched by a fresh `powershell.exe -NoProfile` process and
checks compile, parse, existing-output refusal, full runner execution, source
integrity, and comparison artifacts.

`test-state-authority.ps1` is a report-only regression probe for the G0-C1
consumer rule. It replays a stale active-task conflict against an explicit
PLAN state, requires `memory_state_conflict`, and verifies that PLAN wins while
the memory file remains a reconciliation candidate. It does not install a
session hook or parse arbitrary PLAN prose.
