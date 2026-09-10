# M1-COM1 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size: `104,136,704` bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- VSE probe: `notify-client-sentinel.vse`
- Host harness: `tools/run-m1-com1-notify.ps1`
- Execution API: `GetVScriptEngine(full_path)` + synchronous `RunVScript()`
- Event sink: `_IVScriptEngineEvents::OnNotifyClient` via the Automation TypeLib connection point
- File I/O in VSE probe: none
- Host result file: none; result was captured on stdout
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Acceptance result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Run completes within 30 seconds | `ElapsedMilliseconds=3921` | YES |
| VSE result is PASSED_WARNING | `RunResult=3` | YES |
| Host callback count | `NotifyCount=1` | YES |
| Event ID | `EventId=1001` | YES |
| Host tag | `Tag=4242` | YES |
| Payload item 0 | `Payload0=M1-COM1` | YES |
| Payload item 1 | `Payload1=0` (`in.Index` for the first delivered event) | YES |
| Host error | Empty `Error` field and process exit `0` | YES |
| VSE file output | No file API in probe | OUT OF SCOPE |

## Host result

```json
{"RunResult":3,"ElapsedMilliseconds":3921,"NotifyCount":1,"EventId":1001,"Tag":4242,"Payload0":"M1-COM1","Payload1":"0","Error":""}
```

## Verdict

`M1-COM1 PASS`.

The selected VSE delivery configuration reached `ProcessEvent()`, sent one
structured payload through `NotifyClient()`, and the Automation host received
that payload through `OnNotifyClient` before the synchronous run completed.
This establishes the VSE-to-host data bridge for one event in the local 10.40
runtime.

It does not prove full-trace extraction, summary generation, or AI analysis.
The original VSE-owned external-file requirement remains unproven; a host-side
summary writer is now a validated alternative architecture candidate.

Per scope, E2b, B/C, additional file-path probes, Governance, commit, and push
were not performed.
