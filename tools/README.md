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
chronological event-index ordering, JSON read-back, and trace integrity.

compare-m2-timelines.ps1 compares two normalized timeline JSON artifacts. It
uses a common event-sequence anchor when available and reports a candidate
divergence plus trace-local GUI windows. It does not claim absolute first
divergence, root cause, severity, or PASS/FAIL classification.

localize-trace-mutation.ps1 compares two binary trace files and reports changed
offset ranges plus bounded before/after hex. It localizes bytes only; it does
not assign semantic meaning or safety to the mutation.

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
read-only workflow to a PASS/FAIL pair, invokes both timeline extractions,
invokes the common-anchor comparator, and writes the timeline, comparison,
source-integrity, log, and Markdown report artifacts. It refuses an existing
output directory so prior evidence is not overwritten.

`m2-timeline-extraction.cs` intentionally uses legacy-compatible C# syntax and
reflection-based COM invocation because Windows PowerShell `Add-Type` may use
a compiler that does not accept newer language syntax or implicitly reference
`Microsoft.CSharp.RuntimeBinder`.

`test-demo2-winps-compat.ps1` is the exact-target qualification harness. It is
intended to be launched by a fresh `powershell.exe -NoProfile` process and
checks compile, parse, existing-output refusal, full runner execution, source
integrity, and comparison artifacts.
