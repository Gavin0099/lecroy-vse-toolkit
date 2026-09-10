# M1-E2 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- Script: `open-close-only.vse`
- Execution API: `IUsbTraceForScript::RunVerificationScript(full_path)`
- Delivery configuration: identical to `first-event-sentinel.vse`
- Target: `C:\Temp\vse-io-probe.txt`
- `WriteString()` in probe: no
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Observed result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | Synchronous call returned in `3,980 ms` | YES |
| Result is PASSED_WARNING | `VS_RESULT=PASSED_WARNING (3)` | YES |
| `ProcessEvent()` entry | Same E1 delivery configuration and terminal sentinel | CONFIRMED |
| Open/Close execution path | `PASSED_WARNING` was returned after the `OpenFile()` and `CloseFile()` statements | PASS at execution-path level |
| `WriteString()` present | No `WriteString()` call in the probe | NO, by design |
| Output file exists | `C:\Temp\vse-io-probe.txt` absent after the run | NO |
| Output content correct | No output file to inspect | NOT APPLICABLE |
| Handle value | Reported with `ReportText()` but not returned by this sync API surface | NOT CAPTURED |

## Verdict

`M1-E2 execution-path PASS; physical-artifact NOT PROVEN`.

The `PASSED_WARNING` result confirms that the same bounded event-entry path
used by E1 still completes after the `OpenFile()` and `CloseFile()` statements.
The target file was not observable afterward. Because `WriteString()` was
absent, this run does not test or implicate write-content behavior.

The result narrows the unresolved capability to the `OpenFile()`/
`CloseFile()` path or its file-creation observability in this 10.40 runtime.
It does not by itself establish the meaning of the reported handle value.

Per scope, E3, B/C, Governance, commit, and push were not performed.
