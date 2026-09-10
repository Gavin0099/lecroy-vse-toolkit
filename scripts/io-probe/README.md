# M1-IO probes

These probes isolate VSE external file writing from trace-event traversal. Each
probe performs only this sequence:

    ReportText(actual_path)
    OpenFile()
    ReportText(handle)
    WriteString("hello")
    CloseFile()

The probes do not select trace events. They are run against the known
dp1 hub detect SSD fail-2.usb trace through the LeCroy Automation API so the
same VSE runtime is exercised without scanning the 3.1 million-event path.

| Probe | Target |
| --- | --- |
| absolute-temp.vse | C:\Temp\vse-io-probe.txt |
| trace-folder.vse | GetTraceFilePath() + "vse-io-probe.txt" |
| application-folder.vse | GetApplicationFolder() + "vse-io-probe.txt" |

The raw handle value and actual file existence are evidence. A handle value of
0 is not independently classified as success or failure by these probes.

## M1-IO-PURE gate

The pure-*.vse probes intentionally omit ProcessEvent(). First run PURE-0 with
one pure probe and record whether it starts, finishes, and terminates within the
agreed bound. Do not interpret the missing function alone as proof that no trace
traversal occurred.

Only after PURE-0 passes should the three pure probes be run for A/B/C file
existence and content evidence.

The current execution record is in pure-results.md. PURE-0 did not meet the
bounded-runtime gate, so A/B/C remain intentionally unexecuted.

## M1-LC1 documented lifecycle gate

`lifecycle-minimal.vse` is a separate lifecycle probe added after PURE-0 was
classified as inconclusive. It keeps the documented `OnStartScript()`,
`ProcessEvent()`, and `OnFinishScript()` structure, performs no file I/O, and
sets a FAILED sentinel if `ProcessEvent()` is reached.

The execution record is in lifecycle-minimal-results.md. LC1 completed within
the bound, but the FAILED sentinel was returned, so the non-traversal gate did
not pass and the file-writing probes remain pending.

## M1-IO-B1 bounded first-event I/O

`bounded-first-event-temp.vse` attempts the complete `C:\Temp` file sequence
from the first `ProcessEvent()` path and then requests `PASSED_WARNING`. The
result record is in bounded-first-event-temp-results.md. The run returned
`FAILED` within the bound and produced no file, so `ProcessEvent()` and the I/O
failure point are not individually proven. B/C remain unexecuted.

## M1-E1 first-event delivery sentinel

`first-event-sentinel.vse` copies the event-delivery configuration from
`scripts/hello/trace-info.vse` and contains no file I/O. Its only
`ProcessEvent()` action is to set `_VERIFICATION_PASSED_WARNING`, so the
returned `PASSED_WARNING` value is the event-entry evidence. The execution
record is in first-event-sentinel-results.md.

E1 passed in the bounded 10.40 Automation run. E2 may now be compared against
the same delivery configuration with only the file-I/O operations added.

## M1-E2 Open/Close only

`open-close-only.vse` keeps the E1 delivery configuration and adds only
`OpenFile()` followed by `CloseFile()`. It intentionally contains no
`WriteString()`. The execution record is in open-close-only-results.md.

E2 returned `PASSED_WARNING` within the bound, but no target file was created.
The event-delivery, bounded lifecycle, and Open/Close execution path therefore
remain proven at the script-result level, while physical file creation is not
observed. E3 adds `WriteString()` to test the artifact needed by the product
goal.

## M1-E3 trace-folder WriteString

`write-string-trace-folder.vse` keeps the E1 delivery configuration and adds
the trace-folder path plus one `WriteString()` call to the E2 sequence. The
execution record is in write-string-trace-folder-results.md.

E3 returned `PASSED_WARNING` within the bound, but the expected output beside
the `.usb` trace was not observed. The result is retained as a diagnostic
failure of the physical artifact acceptance, not as a failure of event entry
or terminal completion.

## M1-E3A C:\Temp WriteString controlled comparison

`write-string-temp.vse` is the controlled comparison to E2: it keeps the same
event-delivery configuration and `C:\Temp` path, adding only
`WriteString(handle, "M1-E3A")`. The execution record is in
write-string-temp-results.md.

E3A returned `PASSED_WARNING` within the bound, but the target file was still
absent. This strengthens the evidence that the unresolved issue is the
observable filesystem effect of the VSE file API in this execution context,
not the trace-folder path construction. E2b remains a separate optional probe.

## M1-COM1 NotifyClient sentinel

`notify-client-sentinel.vse` keeps the E1 delivery configuration and sends one
VARIANT-list payload with `NotifyClient(1001, ["M1-COM1", in.Index])` from the
first `ProcessEvent()` path. The host harness is
`tools/run-m1-com1-notify.ps1`; it uses the Automation TypeLib event connection
point and does not write a result file. The execution record is in
notify-client-sentinel-results.md.

COM1 passed: the host received one callback with event ID `1001`, tag `4242`,
and payload `M1-COM1, 0`, while the synchronous run returned
`PASSED_WARNING=3`. This proves the VSE-to-host data bridge, but does not yet
prove external summary generation.

## M1-COM2 real summary bridge

`real-summary-notify.vse` keeps the same delivery configuration and performs
the minimal full-trace counters required by the M1-COM2 acceptance:

    EventCount
    USB3 RX
    USB3 TX
    USB CC

After traversal, `OnFinishScript()` sends exactly one five-item payload:

    ["M1-COM2", EventCount, Usb3RxCount, Usb3TxCount, UsbCcCount]

The host harness is `tools/run-m1-com2-notify.ps1`. It validates the payload
against the known `dp1 hub detect SSD fail-2.usb` baseline and does not write a
file. The execution record is in real-summary-notify-results.md.

COM2 passed on the local USB Protocol Suite 10.40 runtime: `DONE=2`, one host
callback, and all four counts matched the existing `trace-info.vse` evidence.
This proves the real summary bridge, not host-side JSON serialization.

## M1-COM3 host-owned JSON artifact

`tools/run-m1-com3-json.ps1` reuses the unchanged COM2 VSE probe and host
bridge. It adds only host-side serialization to `summary.json`, then reads the
file back with `ConvertFrom-Json` and compares all four fields. The execution
record is in host-summary-json-results.md.

The JSON acceptance passed: the host received one notification, wrote valid
JSON, and read back `3186175`, `632512`, `2553662`, and `1` exactly. A separate
post-run check found an unexplained size and timestamp change in the input
`.usb` file, so input preservation is tracked separately and must be resolved
before calling the repository baseline clean.

## M1-I1 trace mutation isolation

`tools/m1-i1-open-close.cs` and `tools/run-m1-i1-a-open-close.ps1` isolate
Automation `OpenFile()`/`Close()` without VSE. I1-B reuses the COM2 harness on
a separate copy without JSON. I1-C keeps the trace open while the Host writes
JSON to a separate output directory, then closes the trace. The execution
record is in trace-integrity-isolation-results.md.

All three sacrificial-copy stages preserved the same SHA-256, size, and UTC
mtime. The earlier mutation of the original trace was not reproduced, so the
controlled isolation slice passes but the historical discrepancy remains
unknown. `M1-I2` then repeated the exact same-folder COM3 layout on a fresh
sacrificial copy and also preserved hash, size, and UTC mtime. The final I2
record is in exact-com3-integrity-results.md.

M1 is now functionally qualified. The historical mutation remains recorded as
`UNEXPLAINED / NOT REPRODUCED`; it is not treated as proof of a current
workflow defect.
