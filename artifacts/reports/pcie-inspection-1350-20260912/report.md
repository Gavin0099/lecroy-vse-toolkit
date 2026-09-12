# PCIe Trace Inspection

單一 trace 的有限範圍檢視。這份報告不判斷正常／異常，也不提出故障原因。

| 狀態 | 值 |
| --- | --- |
| Extraction | **PASS — bounded first five TLP records** |
| Ground truth | **UNKNOWN** |
| Diagnostic result | **NOT_EVALUATED** |
| Coverage | **FIRST_FIVE_TLP_RECORDS_ONLY** |

## Trace identity

| 欄位 | 值 |
| --- | --- |
| File | `S0-Remove SD7-1350.pex` |
| Local source path | `C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex` |
| Size | 105,224,486 bytes |
| SHA-256 | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Last write (UTC) | `2026-06-11T07:12:55.2721460Z` |

## Runtime and extraction scope

- Software: Teledyne LeCroy PCIe Protocol Analysis 13.26 Build 43 BETA
- Executable SHA-256: `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118`
- VSE script: `scripts/pcie/p0-d1-tlps.pevs`
- Script SHA-256: `91AAA647D24C4785A2C4418066B0D1A4BABF926E4C09B8F1EA86558EE0C507CA`
- Scope: First five TLP callbacks emitted by the unchanged D1 bounded spike; not a full-trace traversal/count.
- Fields actually emitted: `in.Index`, `TimeToText(in.Time)`, `GetEventName()`, `GetChannelName()`, `in.TLPType`, `in.LinkWidth`
- Time source: Vendor-formatted display text from TimeToText(in.Time); coarse seconds only. GUI timestamps are separate corroborating observations.

## Extracted TLP observations

API display time and GUI timestamp are separate measurements. The GUI column is a cross-check observation, not a higher-precision value emitted by the VSE script.

| Packet index | Extractor time | Raw vendor type | Vendor channel | Width | GUI family / subtype | GUI time (sec) |
| ---: | --- | --- | --- | ---: | --- | ---: |
| 1944516 | 4.848 sec | 0xE | Downstream | x1 | Msg / MsgD | 4.847933004000 |
| 1944517 | 4.848 sec | 0x9 | Downstream | x1 | Cfg / CfgRd0 | 4.847933068000 |
| 1944519 | 4.848 sec | 0x9 | Downstream | x1 | Cfg / CfgRd0 | 4.847937356000 |
| 1944521 | 4.848 sec | 0x9 | Downstream | x1 | Cfg / CfgRd0 | 4.847939414000 |
| 1944523 | 4.848 sec | 0x9 | Downstream | x1 | Cfg / CfgRd0 | 4.847948900000 |

Five of five emitted records matched the GUI sample by packet index, raw vendor type, displayed-time rounding, and link width. The visible GUI sequence covers indices 1944516, 1944517, 1944518, 1944519, 1944520, 1944521, 1944522, 1944523, 1944524, 1944525; intervening non-extracted packet indices are 1944518, 1944520, 1944522, 1944524. The next TLP visible beyond the script cap is 1944525; it is context only and is not included in the extraction result.

## Evidence

- [Original VSE extraction output](../../evidence/pcie-staircase-20260912/d1-vendor-saved-output.log.txt) — SHA-256 `31EF4279896C216F4FA6928D275D5D3388F7FAC576A059CF4CBC5926D992EEF3`
- [LeCroy GUI cross-check](../../evidence/pcie-staircase-20260912/d1-gui-crosscheck.png) — SHA-256 `C6FE380483ACDB27775168AA91DA630F282889DFFA1E39CC09C21BC4DFF873A0`
- Structured observations: `observations.json`

## Limitations

- This is a single-trace inspection report, not PASS/FAIL triage.
- Ground truth is UNKNOWN; diagnostic result is NOT EVALUATED.
- Only the first five TLP callbacks emitted by this bounded script are represented; this is not full-trace coverage or a total TLP count.
- Extractor time is coarse vendor display text. More precise values shown are separate GUI cross-check observations.
- The extractor reports the vendor channel label Downstream; physical endpoint mapping is not established.
- No TLP payload, request/completion semantics, suspicious region, or root cause was analyzed.
- The GUI Errors detected! indicator is not interpreted as a device PASS/FAIL result.
- The source capture remains external to this report bundle; its identity is bound by size, modification time, and SHA-256.

Schema: `pcie.trace-inspection-observations/v1`. This inspection-only observation document is not the later F1 finding contract, a normalized PCIe event model, or a USB/PCIe shared schema.
