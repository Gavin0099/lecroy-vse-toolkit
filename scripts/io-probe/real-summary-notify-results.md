# M1-COM2 execution record

## Scope

- Trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- Trace size before/after: `104,136,704` bytes / `104,136,704` bytes
- Trace last write after run: `2026-09-04T11:05:57+08:00`
- Application: Teledyne LeCroy USB Protocol Suite v10.40 (Build 6309)
- VSE probe: `real-summary-notify.vse`
- Host harness: `tools/run-m1-com2-notify.ps1`
- Execution API: `GetVScriptEngine(full_path)` + synchronous `RunVScript()`
- Event sink: `_IVScriptEngineEvents::OnNotifyClient` via the Automation TypeLib connection point
- VSE payload: `NotifyClient(2001, ["M1-COM2", EventCount, Usb3RxCount, Usb3TxCount, UsbCcCount])`
- VSE file I/O: none
- Host result file: none; result was captured on stdout
- Existing probes modified: no
- `trace-info.vse` modified: no
- Trace modified or copied: no

## Acceptance result

| Check | Evidence | Outcome |
| --- | --- | --- |
| Script completes normally | `RunResult=2` (`DONE`) | YES |
| Runtime remains bounded for this known trace | `ElapsedMilliseconds=7082` | YES |
| ProcessEvent traversal count | `EventCount=3186175` | YES |
| USB3 RX count | `Usb3RxCount=632512` | YES |
| USB3 TX count | `Usb3TxCount=2553662` | YES |
| USB CC count | `UsbCcCount=1` | YES |
| NotifyClient callback count | `NotifyCount=1` | YES |
| Event ID | `EventId=2001` | YES |
| Host tag | `Tag=4242` | YES |
| Payload marker | `Marker=M1-COM2` | YES |
| Payload shape | 5 items, no payload conversion error | YES |
| Trace unchanged | Size and last-write timestamp unchanged | YES |
| External summary artifact | No file was requested by this slice | OUT OF SCOPE |

## Host result

```json
{"RunResult":2,"ElapsedMilliseconds":7082,"NotifyCount":1,"EventId":2001,"Tag":4242,"Marker":"M1-COM2","EventCount":3186175,"Usb3RxCount":632512,"Usb3TxCount":2553662,"UsbCcCount":1,"PayloadError":"","Error":""}
```

## Verdict

`M1-COM2 PASS`.

Using the same delivery configuration and the same known `.usb` trace as the
earlier `trace-info.vse` baseline, VSE completed the callback traversal,
computed the four required counts, and delivered them once to the Automation
host without loss or conversion error.

This selects the host-owned artifact route for the next M1 slice:

```text
.usb trace -> LeCroy decoder/VSE -> NotifyClient -> Automation host
```

It does not yet prove `summary.json` generation. That is the separate COM3
slice. The original VSE-owned `OpenFile()` path remains a non-blocking
compatibility investigation and is not required for the selected architecture.

Per scope, JSON serialization, triage findings, GOOD-vs-FAIL comparison,
Governance, commit, and push were not performed.
