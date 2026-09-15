# PCIe-B1c-x2 evidence: HasErrors subtype probe on the hang window (2026-09-15)

Status: **PASS** as a probe; the subtype question stays **open**. None of the 26
candidate error members from the VSE manual is set on any `HasErrors` event.
Descriptive only; ground truth `UNKNOWN`.

## Route and identities

| Item | Identity |
| --- | --- |
| script | `scripts/pcie/b1cx2-haserrors-probe.pevs` (generated from a fixed 26-member list), deployed SHA-256 `ACCDA2A38B79E22048B43C789883518A10C3641F317FEA680F2079738533BD3D` |
| trace | hang converted copy `C6E9646B...` (read-only); original and read-only copy protected |
| run | COM `com-run1`: `COM_RUN_COMPLETE`, finish `DONE` after about 53 s, no error dialog, no GUI input, all three identities unchanged |
| output | `vse-output.txt` SHA-256 `57FD808BA30636BF29B567840F5FB61F2DC75374A0D2FF2599396BF9F1AC8C36` |
| verifier | `verify_b1cx2_haserrors.py`: `PASS_HASERRORS_PROBE_OUTPUT`; range and channel totals close; B1b totals `MATCHED` (1,259,373 events, 384,993 `HasErrors`) |

Ranges inside the B1b window: R1 225041-1096917 (Recovery and link-condition
phases), R2 1096918-1479759 (Downstream Polling phase), R3 1479760-1484414 (after
the 1.312 sec gap). Channel ids: C1 `_CHANNEL_1`, C2 `_CHANNEL_2` (= Downstream by
the sample names), C3 other.

## Results

| Scope | Events | TS1 | TS2 | HasErrors | none of the 26 members set |
| --- | --- | --- | --- | --- | --- |
| R1 | 871,876 | 848,648 | 0 | 2 | 2 |
| R2 | 382,842 | 382,842 | 0 | 382,842 | 382,842 |
| R3 | 4,655 | 3,201 | 1,311 | 2,149 | 2,149 |
| C1 | 2,289 | 994 | 1,241 | 0 | 0 |
| C2 Downstream | 1,257,084 | 1,233,697 | 70 | 384,993 | 384,993 |
| C3 | 0 | 0 | 0 | 0 | 0 |

- `HasErrors` by event type: ordered set 384,993; TLP, DLLP, other 0.
- Range by channel: R1 is Downstream except 1 C1 event; R2 is entirely Downstream;
  R3 has 2,288 C1 events (none with `HasErrors`) and 2,367 Downstream events
  (2,207 TS1, 2,149 with `HasErrors`).
- All 22 samples are TS1 (ordered set type 2) on Downstream: 2 in R1 at LTSSM
  Recovery.RcvrLock (5.12; packets 990799 and 1096917), 10 in R2 at Polling (2.0;
  from 1096918), 10 in R3 at Polling (2.0; from 1479761).

Member presence (non-null) over the 1,259,373 window events:

- present on every event: `ErrorDisparity`, `ErrorSymbol`, `ErrorWrongSymbol`,
  `ErrorDelimiter`, `ErrorEndBad`, `ErrorAlignment`, `ErrorLength`,
  `HasIdleErrors`, `IdleErrorDisparity`, `IdleErrorSymbol`, `IdleErrorSkip`,
  `IdleErrorData`
- present on TLPs or DLLPs only: `BadLCRC` 4, `BadECRC` 4, `MsgErrorG3LenCheck` 4,
  `BadCRC` 147, `InvalidEncoding` 151, `ErrorRsvdFld` 151, `FCError` 105
- never present: `ErrorAllignment` (manual spelling), `TsErrorDataRate`,
  `TsErrorFormat`, `TsErrorParity`, `TsErrorRsrvField`, `G3ErrorFraming`,
  `RsvdField`

## What this establishes

- Every `HasErrors` event in the window is a Downstream TS1. The flagged TS1s are
  in Recovery.RcvrLock (2), Polling before the gap (382,842) and Polling after the
  gap (2,149).
- The error type is not any member this runtime exposes under the manual names.
  The four TS error members that the manual lists as part of `HasErrors` for TS1
  and TS2 are null on every event, so a TS-specific error cannot be read that way.
- Downstream stays in Polling across the gap: its post-gap TS1s (from 1479761)
  carry LTSSM 2.0, the same state as before the gap, so B1b's per-channel change
  detection correctly emitted no new Downstream LTSSM record there.

## Correction for B1c

B1c labels phases by the channel of their starting records. Phase 9 (`LINK_UP`,
Upstream) and phase 10 (Polling, Upstream) therefore read as Upstream, but their
2,149 `HasErrors` TS1s are Downstream, and Downstream Polling continues from phase 7.
B1c already states that counts are not split by channel; with this probe the split
is known for R1-R3 and should be shown. Recorded as a follow-up, not changed in the
committed B1c output.

## Still open

- The actual error behind `HasErrors` on these TS1s. Next evidence options: the
  PETracer GUI packet view of a flagged TS1 (for example packet 1096918), which can
  be combined with the B1c-x1 cross-check; or a COM probe of raw TS fields
  (`TS_LinkNumberList`, `TS_LaneNumberList`, `TS_DataRateList`,
  `TS_TrainingControlList`) comparing flagged and unflagged TS1s.
- Link-condition Up/Down wording (B1c-x1), speed labels.
