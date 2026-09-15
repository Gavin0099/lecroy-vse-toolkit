# PCIe-B1b evidence: hang case window (2026-09-14)

Status: **PASS** (step 0 constants and the bounded window export, 2026-09-15).
Reconstruction only: no link rule, no MUX interpretation, ground truth `UNKNOWN`.

## Step 0: VSE constant values

`scripts/pcie/b1b0-constants.pevs` (deployed SHA-256
`C499CF37361FD0917FB078D52FF47582251D03507D66B188A45F42F1753C1AFE`) printed 52
engine constants through the COM route (`com-run1`: `COM_RUN_COMPLETE`, finish
`DONE`, no error dialog, no GUI input, all three hang file identities unchanged).
`verify_b1b0_constants.py`: `PASS_CONSTANT_PROBE_OUTPUT`, output SHA-256
`7374EBCFB851225470067ADCBAC7A67AE74516B01278F813FCDFCC50DF8BBBBE`; values in
`artifacts/evidence/pcie-b1b-hang-20260914/b1b0-constants/export/constants.json`.

Values needed for decoding:

| Group | Values |
| --- | --- |
| packet events | `_PKT_DLLP` 2, `_PKT_TLP` 3, `_PKT_ORDERED_SET` 5, `_PKT_LINK_CONDITION` 6, `_PKT_EIE_EVENT` 7, `_PKT_INVALID` 9 |
| channels | `_CHANNEL_1` 1, `_CHANNEL_2` 2 |
| link condition | `LINK_DOWN` 1, `LINK_UP` 2, `CLKREQ_UP` 128, `CLKREQ_DOWN` 256 |
| LTSSM main | `UNDEFINED` 0, `DETECT` 1, `POLLING` 2, `CONFIG` 3, `L0` 4, `RECOVERY` 5, `HOT_RESET` 6, `DISABLED` 7, `LOOP_BACK` 8, `L0S` 9, `L1` 10, `L2` 11 |
| LTSSM sub | `RECOVERY_RCVRLOCK` 12, `RECOVERY_RCVRCFG` 13, `RECOVERY_RCVRIDL` 14, `RECOVERY_RCVREQL` 15, `RECOVERY_RCVRSPD` 16, `CFG_LINKWIDTH_STRT` 17, `CFG_LINKWIDTH_ACPT` 18, `CFG_LANENUM_WAIT_ACPT` 19, `CFG_COMPLETE` 20, `CFG_IDLE` 21, `L1_1_OR_L1_2` 25, `LTSSM_NO_STATE` 34 |

Speed codes were not probed; their labels below come from the VSE manual text.

## Decoded B1a samples around the TLP-free stretch

`artifacts/evidence/pcie-b1b-hang-20260914/decoded-b1a-samples.json` (239 rows)
maps the B1a records mechanically with the probed constants. Between packet
225041 and the last TLP 1484414:

| Packet | Time | Channel | Record |
| --- | --- | --- | --- |
| 225041 | 9.512 sec | Upstream | link condition `LINK_DOWN`; LTSSM DETECT (state not valid) |
| 225042 | 9.512 sec | Downstream | NAK DLLP, seq 1682 |
| 225043, 225048 | 9.512 sec | Downstream | `CfgRd0` Tag 6 twice, no Completion observed (G2b, not a B1a record) |
| 225051 | 9.512 sec | Downstream | LTSSM RECOVERY.RCVRLOCK |
| 990789 | 9.538 sec | Downstream | `LINK_DOWN`; LTSSM RECOVERY.RCVRSPD |
| 990790 to 990798 | 9.538 to 9.552 sec | Downstream | `LINK_UP`/`LINK_DOWN` alternating, ending `LINK_UP` |
| 990799 | 9.552 sec | Downstream | LTSSM RECOVERY.RCVRLOCK; speed code 0 (2.5 GT/s), width 1; first sampled error-flag event |
| 1096915 | 9.563 sec | Downstream | `LINK_DOWN`; LTSSM RECOVERY.RCVRSPD |
| 1096916, 1096917 | 9.575 sec | Downstream | `LINK_UP`; LTSSM RECOVERY.RCVRLOCK |
| 1096918 | 9.575 sec | Downstream | LTSSM POLLING (state not valid) |
| 1479760 | 10.912 sec | Upstream | `LINK_UP` |
| 1479845 | 10.912 sec | Upstream | LTSSM POLLING; speed code 0, width 1 |
| 1484025 to 1484147 | 10.912 sec | both | CONFIG.LINKWIDTH_STRT, LINKWIDTH_ACPT, LANENUM_WAIT_ACPT, COMPLETE |
| 1484186 to 1484229 | 10.912 sec | both | RECOVERY.RCVRLOCK, RECOVERY.RCVRCFG |
| 1484273 / 1484298 | 10.912 sec | Downstream / Upstream | LTSSM L0 |
| 1484399 / 1484414 | 10.912 sec | Upstream / Downstream | `VENDOR1` message / `SLOTPOWERLIMIT` message (G3c-0) |

## Limits of this decoding

- LTSSM rows are change points on (state, substate, sub-substate) per channel, not
  every event; link-condition, speed/width and NAK rows are complete (not capped).
- 384,993 error-flag events are known only by total count; 50 samples all fall at
  9.552 to 9.575 sec. Which flags and where the rest lie is unknown.
- Between 9.575 sec and 10.912 sec the samples show no LTSSM change and no link
  condition; 1.26 million delivered events there are not yet broken down.
- The link-condition Up/Down wording is contradicted by the VSE manual text; the
  probed constant names are used here and a GUI cross-check is still open.
- Nothing above is a finding. Whether this sequence is the expected MUX path switch
  is PCIe-B1d; B1b only reconstructs what was captured.

## Window export (packets 225041 to 1484414)

`scripts/pcie/b1b-window-export.pevs` (deployed SHA-256
`0D2B974965F93FD1AAD09E8D57D144407CE43D333D1FBF5CCB5852235B487A30`) through COM
(`window-export/com-run1`: `COM_RUN_COMPLETE`, finish `DONE`, 151 report events,
no error dialog, no GUI input, all three hang file identities unchanged). LTSSM
and speed/width state is tracked from trace start and separately per channel.
`verify_b1b_window.py`: `PASS_WINDOW_EXPORT`, output SHA-256
`E6976E9F9A4F3566C578FBABED453BD51EB99AB55A7A6A747CB1F03FFB185E6F`, timeline.json
`D612F674B9F10A620D98AFE1A7823F8C852EC5BEB9254C5E7841628A89C7FF41`. Checks passed:
segment sums equal the END totals (1,259,373 events, 4 TLPs, 384,993 error-flag
events, 33 segments), every record inside the window and in trace order, and the
four TLP records equal the G1 export rows in the window.

Records: 14 link conditions, 22 LTSSM changes, 1 NAK, 4 TLPs, 2 speed/width
changes, 0 PM DLLPs. A segment starts at each LTSSM change or link condition.

| Seg | Packets | Time | Records at segment start | Counts inside the segment |
| --- | --- | --- | --- | --- |
| 1 | 225041-225050 | 9.512 sec | Upstream `LINK_DOWN`, LTSSM DETECT (not valid) | 10 events: 2 TLP (`CfgRd0` at 225043, 225048), NAK seq 1682 at 225042, 6 FC DLLP |
| 2 | 225051-990787 | 9.512-9.538 sec | Downstream RECOVERY.RCVRLOCK | 765,737 events: TS1 742,531, EIEOS 23,205, EIOS 1; no error flag |
| 3-12 | 990789-990798 | 9.538-9.552 sec | Downstream `LINK_DOWN` with RECOVERY.RCVRSPD, then `LINK_UP`/`LINK_DOWN` alternating, ending `LINK_UP` | one event each |
| 13 | 990799-1096914 | 9.552-9.563 sec | Downstream RECOVERY.RCVRLOCK, speed code 0, width 1 | 106,116 TS1, 1 error-flag event |
| 14-16 | 1096915-1096917 | 9.563-9.575 sec | Downstream `LINK_DOWN` with RECOVERY.RCVRSPD, `LINK_UP`, RECOVERY.RCVRLOCK | one event each (the last a TS1 with an error flag) |
| 17 | 1096918-1479759 | 9.575-9.600 sec | Downstream POLLING (not valid) | 382,842 TS1, every one with an error flag |
| (none) | between 1479759 and 1479760 | 9.600-10.912 sec | no delivered event of any subscribed type | about 1.31 s |
| 18 | 1479760-1479844 | 10.912 sec | Upstream `LINK_UP` | 84 TS1, 84 error-flag events |
| 19 | 1479845-1484024 | 10.912 sec | Upstream POLLING, speed code 0, width 1 | TS1 2,984, TS2 1,196, 2,065 error-flag events |
| 20-27 | 1484025-1484185 | 10.912 sec | both channels CONFIG.LINKWIDTH_STRT, LINKWIDTH_ACPT, LANENUM_WAIT_ACPT, COMPLETE | TS1/TS2 only, no error flag |
| 28-31 | 1484186-1484272 | 10.912 sec | both channels RECOVERY.RCVRLOCK, RECOVERY.RCVRCFG | TS1/TS2 only, no error flag |
| 32-33 | 1484273-1484414 | 10.912 sec | Downstream then Upstream L0 (on DLLPs) | DLLP only (99 FC, 41 other), then TLPs `VENDOR1` 1484399 and `SLOTPOWERLIMIT` 1484414 |

## Limits

- `in.HasErrors` was set on 384,993 events, but none of the individual flags read
  by the script (disparity, symbol, wrong symbol, delimiter, EDB, alignment, idle,
  TS data rate/format/parity/reserved, TLP LCRC, DLLP CRC) was set on any of them.
  Which error type the analyzer flagged is therefore unknown; the member names
  may differ from the manual or the error type may be one not read here.
- Segment counts are not split by channel. Channels are known only for records.
- "No delivered event" between 9.600 and 10.912 sec covers the subscribed types
  (TLP, DLLP, ordered set, link condition, EIE); `_PKT_EIE_EVENT` delivered
  nothing in the whole trace, so electrical idle is not observable this way.
- Link-condition Up/Down wording follows the probed constant names; the GUI
  cross-check is still open. Speed code 0 = 2.5 GT/s is manual text, not probed.
- LTSSM "not valid" is the analyzer's validity flag (`LtssmState[2] == 0`), kept
  as captured.
- This reconstructs the capture. Whether it matches the expected MUX path switch
  is PCIe-B1d; nothing here is a finding.
