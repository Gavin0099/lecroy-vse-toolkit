# M1-IO-B1 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `bounded-first-event-temp.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- Target: `C:\Temp\vse-io-probe.txt`
- Original probes modified: no
- Trace modified or copied: no

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `75 ms` | YES |
| Result is PASSED_WARNING | `VS_RESULT=FAILED (0)`; local type library defines `PASSED_WARNING=3` | NO |
| ProcessEvent path confirmed | Required `PASSED_WARNING` result was not returned | NO direct evidence |
| Output file exists | `C:\Temp\vse-io-probe.txt` absent after the run | NO |
| Output content correct | No output file to inspect | NOT APPLICABLE |
| Full trace traversal | Not established by this probe | UNKNOWN |

## Verdict

`M1-IO-B1 NOT PASS` and `NON-DIAGNOSTIC`.

The run was bounded, but `FAILED (0)` does not distinguish between the
`ProcessEvent()` path not being reached and an execution failure before the
`PASSED_WARNING` assignment. The absent file therefore cannot yet be
classified as an `OpenFile()` failure.

Per the fixed scope, B and C were not executed. No existing probe, trace, or
Governance artifact was changed; commit and push remain out of scope.
