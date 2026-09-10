# M1-E1 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `first-event-sentinel.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- Delivery configuration: copied from `scripts/hello/trace-info.vse`
- File I/O in probe: none
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `3,916 ms` | YES |
| Result is PASSED_WARNING | `VS_RESULT=PASSED_WARNING (3)` | YES |
| `ProcessEvent()` entry | The probe's only path to result `3` is `ProcessEvent()` | CONFIRMED by sentinel |
| File I/O attempted | No `OpenFile()`, `WriteString()`, or `CloseFile()` in the probe | NO, by design |
| Full trace traversal | The terminal result is set on the first delivered event | NOT OBSERVED / NOT REQUIRED |
| `OnFinishScript()` | Out of scope for this slice | NOT MEASURED |

## Delivery configuration

The `OnStartScript()` body uses the same calls already exercised by
`trace-info.vse`:

```text
SendAllChannels();
SendLevel(_PKT);
SendLevel(_TRA);
SendLevel(_SPL_TRA);
SendLevel(_XFER);
SendLevel(_SCSI);
SendLevel(_PHY_TRA);
SendAllTraceEvents();
```

## Verdict

`M1-E1 PASS`.

This 10.40 run directly proves that the selected delivery configuration can
reach `ProcessEvent()` and terminate with `PASSED_WARNING` in bounded time. It
does not prove file output; that is the purpose of the separate E2 comparison.

Per scope, E2, B/C, Governance, commit, and push were not performed.
