# PCIe-B1c-x1/x3 evidence: GUI cross-check of link conditions and flagged TS1 (2026-09-15)

Status: x1 **PASS**; x3 **PASS at sample level** (the analyzer names the TS1 errors in
the GUI; the population breakdown is not established). Descriptive only; ground
truth `UNKNOWN`. Owner authorized the desktop session; performed after commit
`9bb3bdf`.

## Session

- 11:22:38 pre-hash: original `F21FCDEB...` (Archive), converted copy `C6E9646B...`
  (ReadOnly), earlier read-only copy `F21FCDEB...` (ReadOnly).
- `open_and_search.ps1` opened the converted copy (file name read back identical,
  Ready at 11:23:18). Its load check was first patched to identify the trace by the
  MDI child title with ellipsis-safe matching, as already done for `run_vse.ps1`.
- `goto_keep.ps1` used Search > Go to Packet (Ctrl+G, index written and read back)
  for packets 225041, 1479760, 1096918, then 990799, 1479761, with a screenshot after
  each. No other input; no unexpected dialog.
- PETracer closed by `WM_CLOSE` at 11:26:15. Post-hash identical for all three files
  (size, SHA-256, attributes).

Screenshots in `artifacts/evidence/pcie-b1c-x1x3-hang-20260915/` (SHA-256):
`gui-pkt-225041.png` `4C7C7508...`, `gui-pkt-1479760.png` `FF67B516...`,
`gui-pkt-1096918.png` `76992A5A...`, `gui-pkt-990799.png` `9A64BD52...`,
`gui-pkt-1479761.png` `5274A30B...`, `gui-ready.png` `6A6686AE...`.

## x1: link-condition wording

| Packet | GUI | VSE constant from B1b |
| --- | --- | --- |
| 225041 | Link Event "Link Down", time stamp 9.512 211 324 s | `LINK_DOWN` (1) |
| 1479760 | Link Event "Link Up", time stamp 10.911 675 776 s | `LINK_UP` (2) |

The GUI wording agrees with the probed constant names; the VSE manual's swapped
description text is not what the analyzer displays.

## x3: flagged Downstream TS1 in the GUI

All three are `R→` rows at 2.5 GT/s x1, the direction PETracer shows for the
Downstream TS1 flow in these views.

| Packet | B1c phase | GUI error label | Fields shown (red where the GUI marks them) |
| --- | --- | --- | --- |
| 990799 | 4 Recovery.RcvrLock | Training Sequence Error: `TSDataRateErr, TSRsrvErr, TSLaneErr, TSTrainingControlErr` | Link 4, Lane 64, N_FTS 74, RSVD `0, 1`, Data Rate "2.5 GT/s, 8.0 GT/s, Reserved", RSVD `2`, Training Control `0 1 0 0 1 0 1 0`. Neighbouring TS1s 990800 onward show Link 4, Lane 0, N_FTS 254, Training Control all 0, no error. |
| 1096918 | 7 Polling (first flagged TS1 of the phase) | Training Sequence Error: `TSRsrvErr` | Link PAD, Lane PAD, N_FTS 254, RSVD `0, 1, 0`, Data Rate "2.5, 5.0, 8.0, 16.0 GT/s, Reserved", Training Control all 0, Time Delta 1.336 sec |
| 1479761 | 9-10 after the gap (Downstream) | Training Sequence Error: `TSRsrvErr` | same field values as 1096918, Time Delta 5.502 us |

Other rows in the same views, for contrast (no error label):

- Downstream TS1 225052 onward at 5.0 GT/s during Recovery: Link 4, Lane 0,
  N_FTS 254, Data Rate "2.5, 5.0, 8.0, 16.0 GT/s".
- Upstream (`R←`) TS1 from 1479845 at 2.5 GT/s after the gap: Link PAD, Lane PAD,
  N_FTS 128, Data Rate "2.5, 5.0, 8.0 GT/s".

## What this establishes

- The `HasErrors` flag on these TS1s corresponds to analyzer Training Sequence
  errors. For the two Polling samples the named error is `TSRsrvErr`: a reserved
  field in the Downstream TS1 is non-zero and the data-rate field shows a Reserved
  bit. The Recovery sample 990799 carries four TS errors.
- The VSE members `TsErrorDataRate`, `TsErrorRsrvField` and related were null in
  x2, so the GUI is currently the only verified source for these names.

## Not established

- That all 382,842 flagged TS1s in phase 7 or all 2,149 after the gap are
  `TSRsrvErr`; three GUI samples were viewed.
- Why the GUI's next row after 1096918 is packet 1479760 and after 1479761 is
  Upstream 1479845. It looks like collapsed repeated TS1s in this trace view, but the
  view setting was not inspected.
- Any reading of what a reserved-bit TS1 means for this link or product (PCIe-B1d).
