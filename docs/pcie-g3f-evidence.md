# PCIe-G3f Structured Findings — Evidence (2026-09-14)

Status: **G3f PASS (prototype)** for 1350: 16 findings, one per G3e group,
membership unchanged, every candidate in exactly one finding. Findings are
listed in capture order of their primary Go to Packet; this is not a ranking.
Interpretation stays `NOT_EVALUATED`; trace ground truth is UNKNOWN. PETracer
was not opened.

Output `artifacts/evidence/pcie-g3f-20260914/findings.json`, SHA-256 `B36283941560512B24A25C2DB6333AF9A8E4FE8FFFC76B9BAA35DCE581B02936`.
Inputs (unchanged during the run): G3e groups, G3 candidates, G3c nearby
messages, G3d contexts, G2a fields.

```text
python -X utf8 -B scripts/pcie/g3f_findings.py   --groups artifacts/evidence/pcie-g3e-20260914/groups.json   --candidates artifacts/evidence/pcie-g3-20260914/candidates.json   --nearby artifacts/evidence/pcie-g3c-20260914/nearby_messages.json   --contexts artifacts/evidence/pcie-g3d-20260914/contexts.json   --fields artifacts/evidence/pcie-g2a-20260914/export/fields.json   --output-dir artifacts/evidence/pcie-g3f-20260914
```

## Owner decision carried in

G3e rule 2 (shared association lineage) is kept unchanged (option 1). G3f must
show that a group means related evidence, not a proven single local problem.

## What each finding answers

| Question | Field |
| --- | --- |
| Where to look | `where_to_look.primary_go_to_packet` (G3e rule) and one Go to Packet per local segment |
| What was observed | `what_was_observed.candidate_observations` and `local_segments` with anchor TLPs (packet, time, type, Tag, requester, completer, status, candidate roles) |
| Why it was surfaced | `why_surfaced`: detector surfacing text and grouping basis in words |
| What else is nearby | segment `nearby_messages` (G3c, temporal correlation only), `context_refs` to G3d blocks, `gui_crosschecks` |
| What is not known | `not_known`: NOT_EVALUATED, UNKNOWN ground truth, segment/episode limitation, G3c heuristic, unchecked associations, same-key limits |

## Local segments

A group is split for reading only: the G3d context blocks of its members are
merged when their TLP row ranges overlap (G3d's 5-row presentation window).
No new distance threshold is introduced. When a finding has more than one
segment, `not_known` states that grouping does not establish that observations
in separate segments belong to the same failure episode, with the trace span in
packets. All 16 findings have at least two segments, so all 16 carry that
limitation, including F005-F008 whose span is under 500 packets.

G3c messages are placed in the segment containing the anchor G3c measured them
from (`gap_reference_packet`), falling back to context-row containment.

## Corrections made before delivery

The first G3f run was checked finding by finding and not delivered:

1. Some G3c messages (8 TLP rows away) fell outside G3d's 5-row context and were
   listed outside any segment. Fixed by reference-anchor placement; now 0 unplaced.
2. Rows between a G3a request and completion (for example the Msg 2093072 in F010)
   were listed as anchors. Fixed: anchors are only rows marked `ANCHOR_*`.
3. Singletons used group wording in the segment limitation. Fixed with
   candidate-specific wording.

Regression tests cover all three.

## All findings

| Finding | Group | Go to Packet | Members | Trace span (packets) | Local segments | GUI-cross-checked |
| --- | --- | ---: | --- | ---: | --- | --- |
| F001 | G001 | 1944517 | C001, C019 | 149084 | A (4.848 sec): 1944517 CfgRd0 Tag 8 + nearby SLOTPOWERLIMIT 1944516<br>B (4.848 sec): 1944559 CfgRd0 Tag 8<br>C (5.883 sec): 2093601 CfgRd0 Tag 8 | - |
| F002 | G002 | 1944519 | C002, C020 | 149096 | A (4.848 sec): 1944519 CfgRd0 Tag 14 + nearby SLOTPOWERLIMIT 1944516<br>B (4.848 sec): 1944563 CfgWr0 Tag 14<br>C (5.883 sec): 2093615 CfgRd0 Tag 14 | - |
| F003 | G003 | 1944521 | C003, C012, C021, C030 | 148567 | A (4.848 sec): 1944521 CfgRd0 Tag 0; 1944543 CfgRd0 Tag 0; 1944567 CfgWr0 Tag 0 + nearby SLOTPOWERLIMIT 1944516<br>B (5.880 sec): 2093086 MRd(32) Tag 0; 2093088 Cpl Tag 0 UR + nearby ERR_COR 2093072 | C030 |
| F004 | G004 | 1944523 | C004, C022 | 149129 | A (4.848 sec): 1944523 CfgRd0 Tag 5 + nearby SLOTPOWERLIMIT 1944516<br>B (4.848 sec): 1944571 CfgWr0 Tag 5<br>C (5.883 sec): 2093652 CfgRd0 Tag 5 | - |
| F005 | G005 | 1944525 | C005, C023 | 483 | A (4.848 sec): 1944525 CfgRd0 Tag 11 + nearby SLOTPOWERLIMIT 1944516<br>B (4.853 sec): 1945005 MRd(32) Tag 11; 1945008 Cpl Tag 11 UR + nearby ERR_COR 1945029 | C023 |
| F006 | G006 | 1944527 | C006, C015, C024 | 486 | A (4.848 sec): 1944527 CfgRd0 Tag 1; 1944551 CfgRd0 Tag 1 + nearby SLOTPOWERLIMIT 1944516<br>B (4.853 sec): 1945011 MRd(32) Tag 1; 1945013 Cpl Tag 1 UR + nearby ERR_COR 1945029 | - |
| F007 | G007 | 1944531 | C007, C025 | 487 | A (4.848 sec): 1944531 CfgRd0 Tag 7 + nearby SLOTPOWERLIMIT 1944516<br>B (4.853 sec): 1945016 MRd(32) Tag 7; 1945018 Cpl Tag 7 UR + nearby ERR_COR 1945029 | - |
| F008 | G008 | 1944533 | C008, C026 | 490 | A (4.848 sec): 1944533 CfgRd0 Tag 13 + nearby SLOTPOWERLIMIT 1944516<br>B (4.853 sec): 1945021 MRd(32) Tag 13; 1945023 Cpl Tag 13 UR + nearby ERR_COR 1945029 | - |
| F009 | G009 | 1944535 | C009, C027 | 148530 | A (4.848 sec): 1944535 CfgRd0 Tag 3<br>B (5.880 sec): 2093063 MRd(32) Tag 3; 2093065 Cpl Tag 3 UR + nearby ERR_COR 2093072 | - |
| F010 | G010 | 1944537 | C010, C028 | 148538 | A (4.848 sec): 1944537 CfgRd0 Tag 9<br>B (5.880 sec): 2093071 MRd(32) Tag 9; 2093075 Cpl Tag 9 UR + nearby ERR_COR 2093072 | - |
| F011 | G011 | 1944539 | C011, C029 | 148542 | A (4.848 sec): 1944539 CfgRd0 Tag 15<br>B (5.880 sec): 2093079 MRd(32) Tag 15; 2093081 Cpl Tag 15 UR + nearby ERR_COR 2093072 | - |
| F012 | G012 | 1944547 | C013, C031 | 148546 | A (4.848 sec): 1944547 CfgRd0 Tag 4<br>B (5.880 sec): 2093091 MRd(32) Tag 4; 2093093 Cpl Tag 4 UR + nearby ERR_COR 2093072 | - |
| F013 | G013 | 1944549 | C014 | 148973 | A (4.848 sec): 1944549 CfgRd0 Tag 10<br>B (5.883 sec): 2093522 CfgRd0 Tag 10 | - |
| F014 | G014 | 1944553 | C016 | 148997 | A (4.848 sec): 1944553 CfgRd0 Tag 6<br>B (5.883 sec): 2093550 CfgRd0 Tag 6 | - |
| F015 | G015 | 1944555 | C017 | 149009 | A (4.848 sec): 1944555 CfgRd0 Tag 12<br>B (5.883 sec): 2093564 CfgRd0 Tag 12 | - |
| F016 | G016 | 1944557 | C018 | 149020 | A (4.848 sec): 1944557 CfgRd0 Tag 2<br>B (5.883 sec): 2093577 CfgRd0 Tag 2 | - |

## Examples

### F003 (G003)

- **Where to look:** Go to Packet 1944521; segment Go to Packets [1944521, 2093086].
- **What was observed:**
  - C003: CfgRd0 request 1944521 (Tag 0): same association key observed again at 1944543 (CfgRd0) before an associated completion was observed
  - C012: CfgRd0 request 1944543 (Tag 0): same association key observed again at 1944567 (CfgWr0) before an associated completion was observed
  - C021: CfgWr0 request 1944567 (Tag 0): same association key observed again at 2093086 (MRd(32)) before an associated completion was observed
  - C030: MRd(32) request 2093086 (Tag 0) has associated completion 2093088 with status UR
- **Local segments:**
  - A (4.848 sec): 1944521 CfgRd0 Tag 0; 1944543 CfgRd0 Tag 0; 1944567 CfgWr0 Tag 0 + nearby SLOTPOWERLIMIT 1944516
  - B (5.880 sec): 2093086 MRd(32) Tag 0; 2093088 Cpl Tag 0 UR + nearby ERR_COR 2093072
- **Why surfaced:** An associated completion reports a status other than SC.; Same association key observed again before an associated completion was observed in the captured sequence. Grouping basis: a request or completion of one member is an anchor of another, members anchor the same packet, members are on the same G2b same-key association lineage.
- **GUI cross-checks:** [{'candidate_id': 'C030', 'result': 'MATCHED', 'lecroy_view': 'Split Tra 29'}]
- **Not known:**
  - Interpretation NOT_EVALUATED: no statement that this is abnormal, a fault, or related to the reported failure.
  - Ground truth for the trace is UNKNOWN.
  - Grouping expresses a request or completion of one member is an anchor of another, members anchor the same packet, members are on the same G2b same-key association lineage. It does not establish that observations in separate local segments (trace span 148567 packets) belong to the same failure episode.
  - Nearby messages are temporal correlation only; causality is NOT ESTABLISHED. G3c's 64-packet bound is a prototype heuristic chosen after seeing its v1 results.
  - Same-key reappearance does not establish a requester retransmission, an illegal Tag reuse, or a completion missing from the capture.

### F009 (G009)

- **Where to look:** Go to Packet 1944535; segment Go to Packets [1944535, 2093063].
- **What was observed:**
  - C009: CfgRd0 request 1944535 (Tag 3): same association key observed again at 2093063 (MRd(32)) before an associated completion was observed
  - C027: MRd(32) request 2093063 (Tag 3) has associated completion 2093065 with status UR
- **Local segments:**
  - A (4.848 sec): 1944535 CfgRd0 Tag 3
  - B (5.880 sec): 2093063 MRd(32) Tag 3; 2093065 Cpl Tag 3 UR + nearby ERR_COR 2093072
- **Why surfaced:** An associated completion reports a status other than SC.; Same association key observed again before an associated completion was observed in the captured sequence. Grouping basis: a request or completion of one member is an anchor of another, members anchor the same packet, members are on the same G2b same-key association lineage.
- **GUI cross-checks:** none
- **Not known:**
  - Interpretation NOT_EVALUATED: no statement that this is abnormal, a fault, or related to the reported failure.
  - Ground truth for the trace is UNKNOWN.
  - Grouping expresses a request or completion of one member is an anchor of another, members anchor the same packet, members are on the same G2b same-key association lineage. It does not establish that observations in separate local segments (trace span 148530 packets) belong to the same failure episode.
  - Nearby messages are temporal correlation only; causality is NOT ESTABLISHED. G3c's 64-packet bound is a prototype heuristic chosen after seeing its v1 results.
  - Request/completion association for C027 rests on the G2b nearest-preceding same-key rule and was not GUI-cross-checked.
  - Same-key reappearance does not establish a requester retransmission, an illegal Tag reuse, or a completion missing from the capture.

## Limits

- One trace; ground truth UNKNOWN; no causal or failure-episode conclusions.
- Limitation sentences in `not_known` are structured English assembled from fixed
  phrases; plain-language wording for engineers is G7/G8, following the
  human-writing principles recorded in PLAN.
- Nearby messages inherit G3c's prototype 64-packet heuristic; segment context
  inherits G3d's 5-row presentation heuristic.
