# M1-I2 exact COM3 integrity record

## Scope

This is a fresh sacrificial copy using the current trace state. It reproduces
the original COM3 layout and workflow as closely as possible:

```text
stage folder/
├─ dp1 hub detect SSD fail-2.usb
└─ summary.json
```

The run used the unchanged `real-summary-notify.vse` and the unchanged
`tools/run-m1-com3-json.ps1`. The output path was in the same directory as the
sacrificial `.usb` file. The original customer trace was not used.

## Before/after integrity

```text
Before SHA-256:          F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
After SHA-256:           F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
Before size:             103,062,189 bytes
After size:              103,062,189 bytes
Before LastWriteTimeUtc: 2026-09-10T07:01:12.5609905Z
After LastWriteTimeUtc:  2026-09-10T07:01:12.5609905Z
Trace changed:           false
```

## Functional acceptance

```text
RunResult             = 2 (DONE)
NotifyClient count    = 1
Host write completed  = true
Valid JSON            = true
Read-back match       = true
event_count           = 3186175
usb3_rx               = 632512
usb3_tx               = 2553662
usb_cc                = 1
```

Artifact:

`C:\Users\reiko\Desktop\Lecory\m1-i2-sandbox\dp1 hub detect SSD fail-2\summary.json`

## Verdict

`M1-I2 exact COM3 integrity reproduction PASS`.

The exact same-folder COM3 layout did not reproduce the historical trace
mutation. Together with I1-A/I1-B/I1-C, this is sufficient controlled
qualification for the current M1 workflow. The historical COM3 mutation
remains recorded as `UNEXPLAINED / NOT REPRODUCED`; it is not erased or
reclassified as impossible.

The production immutable-input hash guard remains a future safety requirement,
but is not implemented in this M1 slice. M2 triage and Governance adoption
remain separate follow-up slices.
