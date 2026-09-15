# PCIe-B1a evidence: link-layer field probe on the hang trace (2026-09-14)

Status: **PASS** (field verification only). No link rule, no health claim, no MUX
interpretation. Ground truth `UNKNOWN`.

## Inputs and route

| Item | Identity |
| --- | --- |
| trace | converted disposable copy of `Disable ASPM--Insert SD7-hang.pex` (read-only), SHA-256 `C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD` |
| protected, hashed only | original `F21FCDEB...02CD6` and the earlier read-only copy `F21FCDEB...02CD6` |
| script | `scripts/pcie/b1a-link-fields.pevs`, deployed SHA-256 `E314B6B5FF81EF24F2936780B1DA6A0C9F1AB18374B05FA59492EB876DAD39FF` |
| route | COM, `scripts/pcie/com_run_vse.py` (owner decision: COM extended from A1 to probe execution) |
| verifier | `scripts/pcie/verify_b1a_link_fields.py` with the P4a G1a log as TLP cross-check |

## Runs

| Run | Result |
| --- | --- |
| com-run1 (18:00) | `COM_RUN_FAILED`: VSE parse error, negative literal in a global `set` (line 46). Details and the two manual cleanup clicks in `artifacts/evidence/pcie-b1a-hang-20260914/com-run1/NOTE.md`. |
| com-run2 (18:11) | `COM_RUN_COMPLETE`: finish event `DONE` after 30.3 s, 324 report events, no error dialog, no GUI input, all three file identities unchanged, PETracer exited. |

Verifier on com-run2: `PASS_LINK_FIELD_PROBE_OUTPUT`, G1a TLP cross-check
`MATCHED` (704), output SHA-256
`77E20987D70D2EA37869D36DFB01F2882C843F0F788CD768C40A5D61C2C2FA0D`, records.json
`64B27D0C3A28DF0E6103B8C69C9A078ECAF2CF20984B6C0805152AA54295D2FD`.

## Counts (whole trace)

| Field group | Count |
| --- | --- |
| events delivered (TLP, DLLP, ordered set, link condition, EIE) | 3,457,131 |
| TLP / DLLP / ordered set / link condition / EIE | 704 / 2,147,145 / 1,309,169 / 113 / 0 |
| DLLP ACK / NAK / FC / PM / other | 754 / 1 / 2,145,658 / 682 / 50 |
| DLLP bad CRC / TLP bad LCRC | 0 / 0 |
| TS1 / TS2 / EIOS / EIEOS / SKIP / other ordered sets | 1,265,844 / 18,475 / 92 / 24,758 / 0 / 0 |
| events with `in.HasErrors` set | 384,993 |
| events with `in.LtssmState` present / LTSSM changes | 3,457,128 / 119 |
| events with speed / width present / speed-width changes | 3,457,131 / 3,457,131 / 6 |

Populated and usable: DLLP type and `AckNak_SeqNum`, ordered set type, link
condition type (including a `Sideband` channel), `LtssmState` list, speed, link
width, `HasErrors`. `in.BadCRC` and `in.BadLCRC` were readable (all zero).
`_PKT_EIE_EVENT` delivered nothing in this trace.

## Where the sampled records fall

Windows use the TLP-free stretch established by the G1 export: A = up to packet
225048 (last TLP before the stretch), B = 225049 to 1484398, C = from 1484399.

| Kind | A | B | C | Truncated |
| --- | --- | --- | --- | --- |
| LTSSM changes | 98 | 21 | 0 | no |
| link conditions | 100 | 13 | 0 | no |
| speed/width changes | 4 | 2 | 0 | no |
| NAK DLLPs | 1 (packet 225042, Downstream, seq 1682) | 0 | 0 | no |
| error events | 0 of the 50 samples | 50 of 50 | 0 | yes (384,993 total, window split unknown) |

Link-condition records in and next to window B (raw type codes; by constant name
in `VS_constants.inc` 1 = `LINK_CONDITION_LINK_DOWN`, 2 = `LINK_CONDITION_LINK_UP`):

- 225041, 9.512 sec, Upstream, 1
- 990789 to 990798, 9.538 to 9.552 sec, Downstream, alternating 1 and 2 (five pairs)
- 1096915, 9.563 sec, Downstream, 1; 1096916, 9.575 sec, Downstream, 2
- 1479760, 10.912 sec, Upstream, 2

These are listed as captured field values. B1a does not decide what they mean.

## Open items carried into B1b

- **Constant values.** `_PKT_*` and `LTSSM_STATE_*` numeric values are not in
  `VS_constants.inc` or `VSTools.inc` (engine built-ins). The event codes (2, 3,
  5, 6) and LTSSM codes in the records therefore cannot be named yet. B1b starts
  with a tiny probe that prints these constants.
- **Link condition labels.** The VSE manual text pairs `LINK_DOWN = 1` with
  "Link Up" and `LINK_UP = 2` with "Link Down", while the constant names and
  `examp_link_events.pevs` say the opposite. Needs a GUI cross-check before any
  wording.
- **Sideband 128/256** match the CLKREQ constants; the vendor example words them
  "CLKREQ Asserted/Deasserted", again to be cross-checked.
- **Event count vs packet index.** 3,457,131 delivered events exceed the last
  packet index 1,484,414, so one index can yield several callbacks (for example
  per-lane or per-channel ordered sets). B1b must not treat index as a unique
  event key.
- **Speed codes.** Observed speed values 1, 4 and 0 (manual: 0 = 2.5 GT/s, 1 = 5.0,
  4 = 32 GT/s) are raw; a 32 GT/s reading on this device is unverified.
- **Error events.** 384,993 flagged events; only the first 50 are sampled. B1b
  needs per-window counts and the individual error flags.
- **Channel defect in the LTSSM and speed/width change detection (found
  2026-09-15).** The script compared against one previous state for
  `_CHANNEL_1` and one shared previous state for every other channel, so
  Downstream and Sideband events updated the same state. Where the two
  alternate, B1a may report change points that are not changes on either
  channel, so the 119 LTSSM changes and 6 speed/width changes are upper bounds.
  Counts of events, DLLPs, ordered sets, link conditions and errors are not
  affected. B1b tracks channel 1, channel 2 and other channels separately.
