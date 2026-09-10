# M1-E3 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `write-string-trace-folder.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- Target path: `GetTraceFilePath() + "vse-io-probe.txt"`
- Expected physical path: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\vse-io-probe.txt`
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `3,954 ms` | YES |
| Result is PASSED_WARNING | `VS_RESULT=PASSED_WARNING (3)` | YES |
| `ProcessEvent()` entry | Same E1 delivery configuration and terminal sentinel | CONFIRMED |
| `OpenFile()` called | Present before `WriteString()` | ATTEMPTED |
| `WriteString()` called | Present with known content `M1-E3` | ATTEMPTED |
| `CloseFile()` called | Present before terminal result | ATTEMPTED |
| Expected file exists | Expected trace-folder path absent after the run | NO |
| Expected content observed | No expected file to inspect | NOT APPLICABLE |
| Other likely output locations | No matching output observed in the checked application/temp/repo locations | NOT OBSERVED |

## Verdict

`M1-E3 NOT PASS` for the physical-artifact acceptance.

The same bounded event-entry path used by E1 and E2 returned
`PASSED_WARNING=3` after the `OpenFile()`, `WriteString()`, and `CloseFile()`
statements. However, the expected file beside the `.usb` trace was not
observable afterward, so `VSE -> external artifact` is still not proven.

This result does not establish that the file API calls were semantically
successful, nor does it establish that the reported handle value is a failure
code. It does establish that adding the write operation did not prevent the
script from reaching its terminal result.

Per scope, no other output path, B/C probe, E2b probe, Governance, commit, or
push was performed.
