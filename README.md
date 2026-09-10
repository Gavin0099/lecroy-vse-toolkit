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

- M0 repository bootstrap: present.
- M1 runtime traversal: PASS on the known real `.usb` trace under the selected delivery configuration.
- M1-COM1 event bridge: PASS.
- M1-COM2 real summary bridge: PASS; `3,186,175` events, `632,512` USB3 RX, `2,553,662` USB3 TX, and `1` USB CC delivered once to the host.
- M1-COM3 host-owned `summary.json`: JSON write/read-back PASS.
- M1-I1 sacrificial-copy integrity isolation: PASS; the mutation was not reproduced in A/B/C.
- M1-I2 exact same-folder COM3 integrity reproduction: PASS.
- M1 overall: PASS; the historical input `.usb` size/timestamp change remains recorded as `UNEXPLAINED / NOT REPRODUCED`.
- VSE-owned direct file output: not proven and non-blocking for the selected architecture.
- Official LeCroy samples: referenced only; not copied into this repository.

## Repository map

```text
docs/                         Working notes and data-model boundaries
reference/                    Local-installation and sample references
scripts/hello/                M1 execution probe
scripts/m2-packet-extraction-1.vse M2 selected-event extraction probe
scripts/m2-packet-extraction-2.vse M2 LTSSM event extraction probe
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
M2-PACKET-EXTRACTION-2 validate only two selected event paths. AI, RAG,
agents, plugin systems, broad framework abstractions, and higher-level triage
remain outside the current slices.

See [PLAN.md](PLAN.md) for the milestone gate and [docs/vse-api-notes.md](docs/vse-api-notes.md) for the local API evidence boundary.

Governance adoption is recorded as a separate G0 decision. Its source is the
[canonical GitHub repository](https://github.com/Gavin0099/ai-governance-framework),
but the adoption baseline is a confirmed commit SHA, not the moving main
branch. See [docs/governance-adoption.md](docs/governance-adoption.md).
