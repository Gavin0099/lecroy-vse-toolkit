# PCIe-B1c-r1 evidence: post-gap direction correction of the hang training timeline (2026-09-15)

Status: **PASS**. Corrects the presentation of the committed B1c output (`5febc84`)
using the evidence committed in `9bb3bdf` (B1c-x2) and `23fe07c` (B1c-x1/x3). The
original B1c output under `artifacts/evidence/pcie-b1c-hang-20260915/` is kept
unchanged as history; the revision is written to
`artifacts/evidence/pcie-b1c-r1-hang-20260915/`. Descriptive only; no MUX reading;
ground truth `UNKNOWN`.

## What was wrong in B1c

B1c titled each phase with the channel of its starting records. After the 1.312 sec
gap, phase 9 starts with Upstream `LINK_UP` and phase 10 with Upstream Polling, so
both read as Upstream. B1c-x2 showed that all 2,149 `HasErrors` TS1 in packets
1479760-1484414 are Downstream, and Downstream stays in Polling from packet 1096918
because B1b records LTSSM changes per channel and Downstream emitted no new state
there. The B1c output was not wrong in its counts; it hid the second channel.

## Changes in `scripts/pcie/b1c_training_timeline.py`

Optional inputs `--x2-haserrors`, `--x2-summary`, `--gui-observations` (all three
required together). Without them the output is the base B1c (existing tests pass).

- Each phase lists the last LTSSM record of each data channel when it starts
  (`ltssm_at_start`).
- `HasErrors` gets a channel only if the phase lies entirely inside a B1c-x2 range
  and every `HasErrors` event of that range is on one channel; the basis is printed.
  The sum of phase `HasErrors` inside a range must equal the x2 range count, else the
  run stops. Per-phase error subtype stays `UNKNOWN`.
- GUI observations attach to the one phase containing the packet and always carry
  "僅代表此 sample"; a contract check rejects any GUI error label without that mark.
- The flow line names the starting channel and, when `HasErrors` sits on another
  channel, that channel and its carried state.
- Link Down/Up wording moves to a "已核對" section (B1c-x1); the direction unknown is
  narrowed to "split only at R1/R2/R3 range level".
- Inputs are gated: x2 summary must be `PASS_HASERRORS_PROBE_OUTPUT` with B1b totals
  `MATCHED`, and its window must equal the B1b window.

## Result (real data)

Output `training.md` SHA-256
`4372689908AFE578DE14B1917EBC7FF7E93FF176782013B22986BD183ED6F56C`; inputs:
B1b timeline `D612F674...`, x2 `haserrors.json` `84BF5F76...`,
`gui-observations.json` `1D6A2D74...`.

Flow: Detect (start Upstream) → Recovery (Downstream) → link condition ×9 →
Recovery → link condition ×1 → Recovery → Polling (Downstream) → no observed events
(1.312 sec) → link condition ×1 (start Upstream; HasErrors on Downstream, Downstream
still Polling) → Polling (start Upstream; HasErrors on Downstream, Downstream still
Polling) → Configuration (both) → Recovery (both) → L0 (both).

Range checks passed: R1 phases 1-6 `HasErrors` 2 (phases 4 and 6), R2 phase 7
382,842, R3 phases 9-13 2,149 (84 + 2,065), each equal to B1c-x2 and each on
Downstream only.

GUI samples placed: 990799 in phase 4 (four TS errors), 1096918 in phase 7
(`TSRsrvErr`), 1479761 in phase 9 (`TSRsrvErr`), each marked as sample only.

## Not established

- Per-phase channel split of TS1/TS2/DLLP counts (only range level).
- The error subtype of the flagged population; three GUI samples only.
- Speed code labels; the name of `_CHANNEL_1` (not seen in x2 samples).
- Any product or MUX interpretation (PCIe-B1d).
