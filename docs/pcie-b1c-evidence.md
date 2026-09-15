# PCIe-B1c evidence: hang link training timeline (2026-09-15)

Status: **PASS** (descriptive condensation only). No link rule, no MUX reading, no
health claim, ground truth `UNKNOWN`. Built after checkpoint commit `43520b6`.

## Input and route

Offline; PETracer was not run. `scripts/pcie/b1c_training_timeline.py` reads the
B1b export and refuses it unless `summary.json` is `PASS_WINDOW_EXPORT`, names the
same `timeline.json` SHA-256 and was built with the probed constants.

| Item | Identity |
| --- | --- |
| B1b timeline | `artifacts/evidence/pcie-b1b-hang-20260914/window-export/export/timeline.json`, SHA-256 `D612F674B9F10A620D98AFE1A7823F8C852EC5BEB9254C5E7841628A89C7FF41` |
| window | packets 225041 to 1484414 |
| output | `artifacts/evidence/pcie-b1c-hang-20260915/training.md` (SHA-256 `9CF90F46F53928D40BFF644F7F4BBD1B0201E3C3425DD3FF0E0964EA09863C8C`) and `training.json` |

## Condensation rules

- Consecutive B1b segments whose starting LTSSM record has the same main state form
  one phase; sub-states and channels are listed in capture order.
- Consecutive segments started only by link conditions form one phase.
- A display-time jump of at least 0.1 sec between neighbouring segments is shown as a
  "no observed events" phase. The threshold is a presentation choice, not a PCIe
  rule; resolution is the PETracer display value.
- Unknowns carried from B1a/B1b are always printed: `HasErrors` subtype `UNKNOWN`,
  counts not split by channel, `LINK_UP`/`LINK_DOWN` wording not GUI-checked,
  speed labels not probed.
- A contract check rejects judgement wording (for example 異常, 失敗, MUX, BSOD,
  root cause, 正常) and any phase that hides an `UNKNOWN` error subtype.

## Result: 13 phases

Detect (Upstream) → Recovery (Downstream) → link condition ×9 → Recovery
(Downstream) → link condition ×1 → Recovery (Downstream) → Polling (Downstream) →
no observed events (1.312 sec) → link condition ×1 → Polling (Upstream) →
Configuration (both) → Recovery (both) → L0 (both)

| Phase | Packets | Time | Content |
| --- | --- | --- | --- |
| 1 Detect | 225041-225050 | 9.512 | Upstream `LINK_DOWN`, Detect (not valid); NAK seq 1682; `CfgRd0` ×2 |
| 2 Recovery | 225051-990789 | 9.512-9.538 | Downstream RcvrLock then RcvrSpd with `LINK_DOWN`; TS1 742,531, EIEOS 23,205; `HasErrors` 0 |
| 3 link condition | 990790-990798 | 9.538-9.552 | Downstream `LINK_UP`/`LINK_DOWN` ×9 |
| 4 Recovery | 990799-1096915 | 9.552-9.563 | Downstream RcvrLock, speed code 0 x1, then RcvrSpd with `LINK_DOWN`; TS1 106,116; `HasErrors` 1 (`UNKNOWN`) |
| 5 link condition | 1096916 | 9.575 | Downstream `LINK_UP` |
| 6 Recovery | 1096917 | 9.575 | Downstream RcvrLock; `HasErrors` 1 (`UNKNOWN`) |
| 7 Polling | 1096918-1479759 | 9.575-9.600 | Downstream Polling (not valid); TS1 382,842, all with `HasErrors` (`UNKNOWN`) |
| 8 no observed events | between 1479759 and 1479760 | 9.600-10.912 | 1.312 sec |
| 9 link condition | 1479760-1479844 | 10.912 | Upstream `LINK_UP`; TS1 84 with `HasErrors` (`UNKNOWN`) |
| 10 Polling | 1479845-1484024 | 10.912 | Upstream, speed code 0 x1; TS1 2,984, TS2 1,196; `HasErrors` 2,065 (`UNKNOWN`) |
| 11 Configuration | 1484025-1484185 | 10.912 | both channels LinkWidth Start/Accept, Lanenum Wait/Accept, Complete; `HasErrors` 0 |
| 12 Recovery | 1484186-1484272 | 10.912 | both channels RcvrLock, RcvrCfg; `HasErrors` 0 |
| 13 L0 | 1484273-1484414 | 10.912 | both channels L0; FC DLLP 99, other DLLP 41; `Msg` 1484399, `MsgD` 1484414 |

## Checks

- `tests/pcie/test_b1c_training_timeline.py`: phase merging, gap phase, `UNKNOWN`
  subtype, contract rejections, record-outside-segment rejection, summary identity
  check (suite 109 tests OK).
- Phase event counts sum to the B1b total (1,259,373) because every segment belongs to
  exactly one phase.

## Not established

- Whether this flow is the expected SD/SDE MUX path switch (PCIe-B1d).
- Any statement that a phase is unexpected (PCIe-B1e).
- The error subtype, per-channel counts, Up/Down wording, speed labels (see above).
