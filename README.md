# lecroy-vse-toolkit

Experimental toolkit for Teledyne LeCroy USB Protocol Suite VSE scripting, trace extraction, and automated USB protocol analysis.

The repository deliberately stays broader than one sample or one USB class. Its first proof target is narrow:

> Open a real `.usb` trace in LeCroy USB Protocol Suite, send a deterministic summary through the VSE-to-host bridge, and produce a verifiable host-owned trace artifact.

The current posture is an experimental lab/toolkit. It does not claim to be a complete USB analyzer, decoder replacement, AI analyzer, or automation product.

## Current status

- M2-PACKET-EXTRACTION-1: PASS for 166,196 decoded USB3 link-command events
  with index, timestamp, type, JSON read-back, and unchanged sacrificial trace
  integrity. Broader packet coverage is not claimed.
- M2-PACKET-EXTRACTION-2: PASS for 30 decoded USB3 LTSSM state events with
  index, timestamp, type, JSON read-back, and unchanged sacrificial trace
  integrity. Decoded state names are not claimed.
- M2-PACKET-EXTRACTION-3: PASS for 47,006 decoded USB3 LFPS events with
  event identity, LFPS-specific raw fields, JSON read-back, and unchanged
  sacrificial trace integrity. Semantic enum names are not claimed.
- M2-4 / DEMO-1: combined PASS/FAIL timeline and candidate-divergence path
  demonstrated and qualified for the controlled source-preserving read-only
  mode. DEMO-I1 recorded a prior PASS working-copy mutation; DEMO-I2 proved
  that the preserved source artifact remained unchanged while a separate
  read-only working copy completed the same extraction.

- M0 repository bootstrap: present.
- M1 runtime traversal: PASS on the known real `.usb` trace under the selected delivery configuration.
- M1-COM1 event bridge: PASS.
- M1-COM2 real summary bridge: PASS; `3,186,175` events, `632,512` USB3 RX, `2,553,662` USB3 TX, and `1` USB CC delivered once to the host.
- M1-COM3 host-owned `summary.json`: JSON write/read-back PASS.
- M1-I1 sacrificial-copy integrity isolation: PASS; the mutation was not reproduced in A/B/C.
- M1-I2 exact same-folder COM3 integrity reproduction: PASS.
- M1 overall: PASS; the historical input `.usb` size/timestamp change remains recorded as `UNEXPLAINED / NOT REPRODUCED`.
- DEMO-I2 source integrity: PASS for the preserved source artifact and this
  read-only working-copy execution. Universal immutability is not claimed.
- DEMO-2 one-click runner: implemented and self-tested; user test pending.
  It creates read-only sandbox copies, runs both timelines, verifies source
  identity, and writes comparison/report artifacts.
- DEMO-2-WINPS-COMPAT: PASS on a fresh Windows PowerShell 5.1 process using
  the exact repository-relative PASS/FAIL traces. Universal performance
  qualification is not claimed.
- VSE-owned direct file output: not proven and non-blocking for the selected architecture.
- Official LeCroy samples: referenced only; not copied into this repository.

## Repository map

```text
docs/                         Working notes and data-model boundaries
reference/                    Local-installation and sample references
scripts/hello/                M1 execution probe
scripts/m2-packet-extraction-1.vse M2 selected-event extraction probe
scripts/m2-packet-extraction-2.vse M2 LTSSM event extraction probe
scripts/m2-packet-extraction-3.vse M2 LFPS event and field extraction probe
scripts/m2-packet-extraction-4.vse M2 combined timeline extractor
run-demo.ps1                  DEMO-2 one-click PASS/FAIL runner
docs/demo-1-pass-fail-results.md  PASS/FAIL candidate comparison evidence
docs/demo-2-winps-compatibility-results.md  Windows PowerShell 5.1 evidence
scripts/packet-dump/          Reserved for M2
scripts/transfer-dump/        Reserved for M3
samples/                      External-input policy
tools/                        Automation/tooling boundary
tests/fixtures/               Fixture policy and future replay inputs
```

## M1 quick start

1. Open a known `.usb` trace in LeCroy USB Protocol Suite.
2. Load the repo script `scripts/hello/trace-info.vse` through the VSE interface. If the GUI requires a filesystem copy, place it in a dedicated script subdirectory under `C:\Users\reiko\Desktop\Lecory`; keep it separate from the trace directories. The repo remains the development source; the Desktop directory is only the GUI test workspace.
3. Confirm that the installed `VSTools.inc` is available from the LeCroy VFScripts installation path. Do not copy that vendor include into the repo.
4. Run the script to completion.
5. For the validated COM2 bridge, run `tools/run-m1-com2-notify.ps1` with the known trace and `scripts/io-probe/real-summary-notify.vse`. The host prints the received summary payload as JSON and validates the fixed baseline.
6. Record the trace identity, application version, script path, staging path, host result, and observed event count in the test notes. Do not commit the trace unless its license and size are known.

The COM2 probe selects the installed VSE levels `_PKT`, `_TRA`, `_SPL_TRA`,
`_XFER`, `_SCSI`, and `_PHY_TRA`, then requests all trace-event types
relevant to those levels. Its payload counts events delivered to
`ProcessEvent()` under that selection. It must not be interpreted as a
complete trace-event count for every trace, version, or configuration.

## DEMO-2 quick start

Run this from the repository root with a new output directory:

```powershell
.\run-demo.ps1 `
  -PassTrace "C:\path\to\pass.usb" `
  -FailTrace "C:\path\to\fail.usb" `
  -Output ".\demo-output"
```

The runner does not pass the source files to VSE. It records their identity,
creates read-only copies under `demo-output\sandbox`, runs the same extractor
on both copies, and writes `report.md`, `comparison.json`, and
`source-integrity.json`. Use a new output directory for each run; existing
directories are rejected to protect prior evidence.

For an exact Windows PowerShell 5.1 qualification, run the compatibility
harness from `powershell.exe`:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\test-demo2-winps-compat.ps1 `
  -PassTrace ".\dp1 hub detect SSD Ex power ok-4.usb" `
  -FailTrace ".\dp1 hub detect SSD fail-2.usb" `
  -Output ".\demo-winps-compat-output"
```

## Scope boundary

The deterministic path comes first:

```text
.usb trace -> LeCroy decoder -> VSE -> NotifyClient -> host artifact -> triage -> optional AI explanation
```

The toolkit is a triage assistant, not a replacement for the LeCroy GUI. Its
first useful output should identify suspicious timestamps, event windows, and
nearby evidence so an engineer can return to the GUI for packet-level
verification.

Packet extraction, ordering, timestamps, addresses, endpoints, and protocol
fields remain deterministic. M2-PACKET-EXTRACTION-1 and
M2-PACKET-EXTRACTION-2 and M2-PACKET-EXTRACTION-3 validate only three selected
event paths. AI, RAG, agents, plugin systems, broad framework abstractions, and
higher-level triage remain outside the current slices.

See [PLAN.md](PLAN.md) for the milestone gate and [docs/vse-api-notes.md](docs/vse-api-notes.md) for the local API evidence boundary.

Governance adoption is recorded as a separate G0 decision. Its source is the
[canonical GitHub repository](https://github.com/Gavin0099/ai-governance-framework),
but the adoption baseline is a confirmed commit SHA, not the moving main
branch. See [docs/governance-adoption.md](docs/governance-adoption.md).
