# M1: trace-info

`trace-info.vse` is the minimum execution probe. It requests all channels and trace events, observes callback delivery, and writes a bounded summary.

It does not parse packet payloads, reconstruct transfers, or decide whether a trace is correct.

The output file is created in the same folder as the input trace through the documented `GetTraceFilePath()` helper. The script reports the concrete path when it finishes.

For manual GUI execution, `C:\Users\reiko\Desktop\Lecory` is the current trace workspace. Keep any temporary copy of this repository's `.vse` script in a dedicated child directory, and keep the installed vendor `VSTools.inc` in the LeCroy installation.
