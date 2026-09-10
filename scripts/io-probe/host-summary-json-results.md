# M1-COM3 execution record

## Scope

- Input trace: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\dp1 hub detect SSD fail-2.usb`
- VSE probe: `real-summary-notify.vse` (unchanged from M1-COM2)
- Host harness: `tools/run-m1-com3-json.ps1`
- Output artifact: `C:\Users\reiko\Desktop\Lecory\dp1 hub detect SSD fail-2\summary.json`
- Serialization: host-side `ConvertTo-Json` plus UTF-8 `File.WriteAllText()`
- VSE changes: none
- VSE-owned `OpenFile()` output: none
- Existing probes modified: no

## JSON acceptance result

| Check | Evidence | Outcome |
| --- | --- | --- |
| `summary.json` exists | `OutputExists=true` | YES |
| Valid JSON | `ConvertFrom-Json` succeeded | YES |
| Host received exactly one notification | `host_received_notify=1` | YES |
| Host write completed | `host_write_completed=true` | YES |
| Read-back values match | `read_back_match=true` | YES |
| `event_count` | `3186175` | YES |
| `usb3_rx` | `632512` | YES |
| `usb3_tx` | `2553662` | YES |
| `usb_cc` | `1` | YES |

## Artifact content

```json
{
  "event_count": 3186175,
  "usb3_rx": 632512,
  "usb3_tx": 2553662,
  "usb_cc": 1
}
```

## Host result

```json
{"output_path":"C:\\Users\\reiko\\Desktop\\Lecory\\dp1 hub detect SSD fail-2\\summary.json","summary_json_exists":true,"valid_json":true,"host_received_notify":1,"host_write_completed":true,"read_back_match":true,"event_count":3186175,"usb3_rx":632512,"usb3_tx":2553662,"usb_cc":1,"bridge_run_result":2,"bridge_elapsed_milliseconds":5911}
```

## Input-integrity observation

The JSON acceptance passed, but a separate integrity check found an
unexplained input-file change after this run:

```text
Before COM3 (last recorded by M1-COM2): 104,136,704 bytes
After COM3:                              103,062,189 bytes
After COM3 last write:                   2026-09-10T15:01:12+08:00
```

No `.bak`, `.tmp`, or lock file was present beside the trace, and no LeCroy
GUI process was running during the post-run check. The COM3 wrapper contains
no trace-write operation; the cause of the mutation is therefore UNKNOWN.
The leading hypothesis is an interaction in the Automation trace open/close
path, but that is not confirmed.

## Verdict

`M1-COM3 JSON artifact acceptance PASS`.

The host-side artifact path is proven, including write and read-back
verification. `M1 overall` is not advanced to a clean baseline yet because
the unexpected input-file mutation requires a separate integrity decision.
Do not interpret this record as proof that the trace is safely read-only.

COM3 did not begin timeline extraction, triage rules, HTML reporting, AI
analysis, Governance adoption, commit, or push.

## Follow-up disposition

`M1-I2` later repeated the exact same-folder COM3 layout on a fresh sacrificial
copy. The trace remained unchanged and the JSON read-back passed. The
historical mutation recorded above remains `UNEXPLAINED / NOT REPRODUCED`, but
it no longer blocks the controlled M1 workflow qualification. See
`exact-com3-integrity-results.md`.
