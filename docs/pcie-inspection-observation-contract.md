# PCIe Single-Trace Inspection Observation Contract (F0a)

Status: first bounded implementation for the 1350 trace, 2026-09-12.

## Purpose and boundary

This contract supports a single-trace inspection report. It records trace
identity, what the current bounded VSE script emitted, and which rows were
visually checked against the LeCroy GUI. It does not classify the trace as
normal or abnormal and contains no findings, divergence, suspicion, score,
severity, or root-cause field.

[`pcie-trace-inspection-observations.schema.json`](../schemas/pcie-trace-inspection-observations.schema.json)
defines the output shape. Its scope is this PCIe inspection report only. It is not the F1 finding
contract, a canonical normalized event format, or a USB/PCIe common schema.
Future code may reuse safe rendering or evidence-linking mechanics; F1 must
make its own evidence-backed field decisions after E3e.

## Status vocabulary

- `extraction = PASS_BOUNDED`: the retained VSE output has the known D1 header,
  exactly five TLP rows, the normal `D O N E !!!` marker, no known runtime-error
  text, matching trace/script/runtime identities, and five matching GUI rows.
- `ground_truth = UNKNOWN`: no engineer-qualified PASS/FAIL label is available.
- `diagnostic_result = NOT_EVALUATED`: no symptom-specific comparison or
  diagnostic decision ran.
- `coverage = FIRST_FIVE_TLP_RECORDS_ONLY`: no total trace count or full-trace
  traversal is inferred.

The report uses neutral presentation for all three status values. It must not
style extraction PASS as device health or imply that ground truth is known.

## Observation fields

Each row preserves the extractor's packet index, event-family text, vendor
channel label, raw vendor TLP type code, link width, and the exact coarse time
display emitted by `TimeToText(in.Time)`. GUI family/subtype, GUI timestamp,
and link width live in a separate `gui_crosscheck` object; they are not
backfilled into extractor output. The current script does not parse TLP
payload fields, request/completion semantics, tags, or full timestamps.

`gui_context` is explicitly screenshot-only. It can name the packet indices
visible between extracted rows and the next TLP visible beyond the cap, but
those rows do not become extracted observations.

## Evidence binding and generation

The input manifest
`samples/pcie/inspection-1350-evidence.json` binds a local external trace,
PETracer executable, unchanged VSE script, original VSE output log, and GUI
cross-check image by path and SHA-256. The builder verifies every identity,
the trace size/UTC modification time, the five log rows, normal completion,
and row-by-row GUI agreement before it creates output. It reads and hashes the
trace but does not open, convert, or analyze its packet contents.

Run from the repository root:

```powershell
python scripts/pcie/build_inspection_report.py `
  --manifest samples/pcie/inspection-1350-evidence.json `
  --output-dir artifacts/reports/pcie-inspection-1350-20260912
```

The new output directory contains `observations.json`, `report.md`, and
`report.html`. Both renderers reload and consume the saved JSON. HTML is
offline, has no scripts or external resources, and escapes evidence-derived
text. Existing output directories are never overwritten. The `.pex` remains
outside the report bundle and Git; the report contains its identity and local
source path, not the binary.

## First sample and acceptance boundary

The first report uses `S0-Remove SD7-1350.pex`, the trace with a retained clean
five-row GUI comparison image and VSE output. It displays API time such as
`4.848 sec` separately from the more detailed GUI time such as
`4.847933004000 sec`. This separation is essential: the latter was read from
the GUI and was not emitted by the current script.

Automated tests check parsing, completion/error rejection, identity drift,
cross-check disagreement, HTML escaping, and same-source MD/HTML rendering.
Local rendering review can establish readability and claim boundaries; it
does not stand in for an engineer's feedback about which information they
need. The first bundle is ready for that review, while F0e external UX
acceptance remains pending.
