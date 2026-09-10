# M1-IO-PURE execution record

## Scope

- Trace: C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb
- Trace size: 104,136,704 bytes
- Application: Teledyne LeCroy USB Protocol Suite v10.40
- Execution surface: LeCroy Automation API
- Original probes modified: no
- Trace modified or copied: no

## PURE-0

- Probe: pure-absolute-temp.vse
- ProcessEvent() defined: no
- RunVScriptEx() completion: not obtained
- Runtime bound: not met; no completion within 30 seconds
- Full traversal observed: unknown
- Output file C:\Temp\vse-io-probe.txt: absent
- Result: NOT PASS

Per the stop condition, PURE-A, PURE-B, and PURE-C were not executed.

This result does not prove that omitting ProcessEvent() causes full traversal.
It proves only that this execution path did not produce a bounded completion
under the tested VSE 10.40 Automation context.
