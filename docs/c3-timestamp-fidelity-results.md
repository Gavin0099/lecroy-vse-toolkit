# C3 Timestamp Fidelity Results

Date: 2026-09-11

## Objective

Verify whether the raw VSE event time can cross the VSE -> NotifyClient -> COM
Host -> JSON path without being reduced to the rounded `TimeToText()` display
value. This slice does not modify the comparator or alignment logic.

The installed VSE template documents `in.Time` as a two-element list in the
form `[seconds, nanoseconds]`. The C3 probe exports both integer components,
the existing human-readable `TimeToText(in.Time)` value, and a checked Host
derived `timestamp_ns` integer.

## Qualification command

The probe ran in a fresh Windows PowerShell 5.1 process against the read-only
FAIL sandbox copy from the DEMO-C2 qualification:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command `
  '& .\tools\run-c3-timestamp-fidelity.ps1 `
    -TracePath ''.\demo-output-c2-qualification-20260911\sandbox\fail\dp1 hub detect SSD fail-2.usb'' `
    -ScriptPath ''.\scripts\c3-timestamp-fidelity.vse'' `
    -OutputPath ''.\c3-output-20260911-v3\timestamp-fidelity.json'''
```

## Observed result

| Check | Result |
| --- | --- |
| Windows PowerShell | 5.1.26100.9444 / Desktop |
| VSE run result | `2` |
| VSE finished result | `2` |
| Runtime | 6,369 ms |
| NotifyClient batches | 190 plus one summary |
| Declared LFPS events | 47,006 |
| Host reconstructed events | 47,006 |
| Raw nanosecond components observed | 47,006 / 47,006 |
| Event order | PASS |
| JSON read-back timestamp fields | PASS |
| Trace integrity | PASS |
| Comparator changed | NO |

## Ground-truth cross-check

The engineer-labeled GUI reference was `21.789454560 sec`. The C3 output
contains an LFPS event with:

```text
index                 = 3082542
timestamp_seconds     = 21
timestamp_nanoseconds = 789454560
timestamp_ns          = 21789454560
timestamp_text        = 21.789 sec
```

The derived integer timestamp matches the reference exactly, with a measured
difference of `0 ns`. The human display remains rounded, but the machine
timestamp is not rounded.

## Layer result

```text
SOURCE_TIMESTAMP_PRECISION = OBSERVED: seconds + nanoseconds
COM_TIMESTAMP_PRECISION    = PRESERVED
HOST_TIMESTAMP_PRECISION   = PRESERVED
JSON_TIMESTAMP_PRECISION   = PRESERVED / read-back verified
EVENT_ORDER                 = UNCHANGED
EVENT_COUNT                 = UNCHANGED
SOURCE_PRECISION_LIMITED    = NO
```

## Claim boundary

C3 proves timestamp fidelity for this VSE 10.40 path and this selected LFPS
event extraction. It does not prove that every VSE event class exposes the
same time representation, and it does not improve PASS/FAIL semantic
alignment. A precise timestamp can still identify the wrong aligned region;
that remains C4 work.
