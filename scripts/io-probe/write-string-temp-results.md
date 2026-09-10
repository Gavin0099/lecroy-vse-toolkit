# M1-E3A execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `write-string-temp.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- Target: `C:\Temp\vse-io-probe.txt`
- Comparison baseline: `open-close-only.vse` (M1-E2)
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Controlled comparison

| Dimension | M1-E2 | M1-E3A |
| --- | --- | --- |
| Event-delivery configuration | Same | Same |
| Target path | `C:\Temp\vse-io-probe.txt` | `C:\Temp\vse-io-probe.txt` |
| OpenFile | yes | yes |
| WriteString | no | `M1-E3A` |
| CloseFile | yes | yes |
| Terminal result | `PASSED_WARNING (3)` | `PASSED_WARNING (3)` |
| Output file | absent | absent |

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `3,891 ms` | YES |
| Result is PASSED_WARNING | `VS_RESULT=PASSED_WARNING (3)` | YES |
| `ProcessEvent()` entry | Same E1 delivery configuration and terminal sentinel | CONFIRMED |
| `OpenFile()` path | Called before `WriteString()` | EXECUTION PATH COMPLETED |
| `WriteString()` path | Called with known content `M1-E3A` | EXECUTION PATH COMPLETED |
| `CloseFile()` path | Called before terminal result | EXECUTION PATH COMPLETED |
| Output file exists | `C:\Temp\vse-io-probe.txt` absent after the run | NO |
| Output content correct | No output file to inspect | NOT APPLICABLE |

## Verdict

`M1-E3A NOT PASS` for the physical-artifact acceptance.

With the absolute path held constant, adding `WriteString()` did not change
the observable result: the script still returned `PASSED_WARNING=3`, but no
file was present. The event-entry and bounded terminal path are therefore
proven, while the VSE-to-filesystem artifact remains unproven in this 10.40
Automation context.

This evidence does not assign failure semantics to the handle value and does
not prove whether VSE materialized the file elsewhere. It does make the
trace-folder path construction a less likely explanation for the missing
artifact.

Per scope, E2b, B/C, Governance, commit, and push were not performed.
