# M1-LC1 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `lifecycle-minimal.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- File I/O in probe: none
- Original probes modified: no
- Trace modified or copied: no

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `732 ms` | YES |
| Result is PASSED | `VS_RESULT=FAILED (0)`; local type library defines `PASSED=1` and `FAILED=0` | NO |
| `ProcessEvent()` reached | The only explicit FAILED path is the `ProcessEvent()` sentinel | YES, sentinel evidence |
| `OnFinishScript()` directly observed | No report stream or persistent callback state is exposed by this synchronous API run | UNKNOWN |
| Full trace traversal | Not established by this probe | UNKNOWN |

## Verdict

`M1-LC1 NOT PASS`.

The documented lifecycle-shaped script completed quickly, but at least one
event reached `ProcessEvent()`, which changed the result to FAILED. This does
not prove a full trace traversal; it proves only that this execution context
dispatches an event without explicit level-selection calls. `PURE-0` remains
inconclusive because it omitted the documented `ProcessEvent()` function.

Per the LC1 gate, the A/B/C file-writing probes were not executed. Governance,
trace copying, and commit/push remain out of scope.
