# VSE API notes

These notes describe the locally installed LeCroy USB Protocol Suite surface inspected on 2026-09-10. They are working notes, not a replacement for the installed VSE manual.

## Observed script shape

The installed examples use:

```text
%include "VSTools.inc"
OnStartScript() { ... }
ProcessEvent() { ... }
OnFinishScript() { ... }
```

The input context documented by the installed template includes `in.Index`, `in.Time`, `in.Channel`, `in.Level`, `in.TraceEvent`, `in.Speed`, `in.Direction`, and `in.Notification`. Additional fields depend on the selected decoded event.

## Observed primitives used by M1

- `SendAllChannels()` selects events from all channels.
- `SendLevel(level)` adds a supported transaction level to the selection. The installed VSE manual lists `_PKT`, `_TRA`, `_SPL_TRA`, `_XFER`, `_SCSI`, and `_PHY_TRA`.
- `SendAllTraceEvents()` requests all trace-event types.
- `GetTraceName()` returns the current trace name/path in the installed examples.
- `GetTraceStartTime()` and `GetTraceEndTime()` expose trace time boundaries.
- `TimeToText()` formats a VSE time value for text output.
- `GetChannelName()` and `GetEventName()` are helper functions in `VSTools.inc`.
- `GetTraceFilePath()`, `OpenFile()`, `WriteString()`, and `CloseFile()` are used by the M1 probe for a generated file next to the input trace. This keeps the result path visible and avoids relying on an application-data directory that may not be writable in the current installation.
- `ScriptForDisplayOnly()` is used when the script is an observation/reporting probe rather than a pass/fail verification.
- `Complete()` returns control after processing the current event.

M1 uses only these observed shapes and keeps the output human-readable until the runtime path is proven.

## Local references inspected

The vendor files remain outside this repository:

- `Scripts/VFScripts/VSTemplate.vs_`
- `Scripts/VFScripts/VSTools.inc`
- `Scripts/VFScripts/VS_constants.inc`
- `Scripts/VFScripts/Examples/zExample1.vse`
- `Scripts/VFScripts/Examples/zExampleTra.vse`
- `Scripts/VFScripts/Examples/zExampleXfer.vse`
- `Scripts/VFScripts/Examples/zzExamplePwr.vse`

## Not yet verified

- Successful M1 execution on a real `.usb` trace.
- Whether every USB Protocol Suite version resolves the include from the same directory.
- Whether `SendAllTraceEvents()` delivers every visible event for every protocol/configuration.
- Whether the application-data output location is writable under all user permissions.
- A headless command-line runner for VSE.
