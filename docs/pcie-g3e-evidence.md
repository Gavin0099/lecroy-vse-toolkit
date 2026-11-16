# PCIe-G3e Candidate Grouping — Evidence (2026-09-14)

Status: **G3e PASS (prototype)** for 1350: 31 candidates in 16 groups, each
candidate in exactly one group. Groups follow shared evidence only; the group
count had no target. No severity, confidence, priority, fault type or
interpretation (`interpretation: NOT_EVALUATED`). PETracer was not opened.

Output `artifacts/evidence/pcie-g3e-20260914/groups.json`, SHA-256 `8D6632799C332DE6D8F3B4C992FD13AF95F9A111F6C5A65B5956B6F77C5AFB3C`.

```text
python -X utf8 -B scripts/pcie/g3e_groups.py   --candidates artifacts/evidence/pcie-g3-20260914/candidates.json   --associations artifacts/evidence/pcie-g2b-20260914/associations.json   --nearby artifacts/evidence/pcie-g3c-20260914/nearby_messages.json   --protected-outputs <G2b associations> <G3 candidates> <G3c nearby> <G3d contexts>   --output-dir artifacts/evidence/pcie-g3e-20260914
```

## Merge rules (owner decision 2026-09-14, fixed before results)

Automatic merge only when two candidates have at least one strong relationship:

1. `shared_anchor_packet`: they anchor the same packet.
2. `shared_association_lineage`: their G2b same-key reissue chains end at the same request.
3. `request_or_completion_is_other_candidate_anchor`: a G3a request or completion is
   another candidate's anchor (recorded in addition to rule 1).

Never merge on their own (kept only as `auxiliary_descriptors_not_used_for_grouping`):
same display time, same nearby message, overlapping context, same RequesterId,
same Tag, same completion status. Candidates without a strong relationship stay
singletons. Primary Go to Packet is deterministic: earliest request packet among
member anchors, else earliest anchor packet. Group IDs follow that packet.

## Invariants checked

- All 31 candidates appear, none twice (enforced in code).
- Every group records `grouping_basis` (`none_singleton` for singletons) and its edges.
- Earlier outputs unchanged (SHA-256 before and after the run):

| Protected output | SHA-256 |
| --- | --- |
| `artifacts/evidence/pcie-g2b-20260914/associations.json` | `BDF7D1C20A4948E2497FC6C8F4A8AE6A5491D9CE9D1D162365C3696B41139A12` |
| `artifacts/evidence/pcie-g3-20260914/candidates.json` | `290FDE9569356CBE73B21735AF261DCC59FB5EBC4563E4A87DE12ECF4C2F181E` |
| `artifacts/evidence/pcie-g3c-20260914/nearby_messages.json` | `9E9AC2EF885687356ADE17D6DB79A7D33475ECD7BA0078FE730B0A811D608EF3` |
| `artifacts/evidence/pcie-g3d-20260914/contexts.json` | `8C3D00FFEF860F44D171A9E96437D3F36EB4A760B9E075AF6818C323A280D74D` |

## Result

| Group | Primary Go to Packet | Members | Grouping basis | Lineage packet span | Anchor display times (aux) | Nearby messages from G3c (aux) |
| --- | ---: | --- | --- | ---: | --- | --- |
| G001 | 1944517 | C001, C019 | shared_anchor_packet, shared_association_lineage | 149084 | 4.848 sec | SLOTPOWERLIMIT 1944516 |
| G002 | 1944519 | C002, C020 | shared_anchor_packet, shared_association_lineage | 149096 | 4.848 sec | SLOTPOWERLIMIT 1944516 |
| G003 | 1944521 | C003, C012, C021, C030 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 148565 | 4.848 sec, 5.880 sec | SLOTPOWERLIMIT 1944516, ERR_COR 2093072 |
| G004 | 1944523 | C004, C022 | shared_anchor_packet, shared_association_lineage | 149129 | 4.848 sec | SLOTPOWERLIMIT 1944516 |
| G005 | 1944525 | C005, C023 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 480 | 4.848 sec, 4.853 sec | SLOTPOWERLIMIT 1944516, ERR_COR 1945029 |
| G006 | 1944527 | C006, C015, C024 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 484 | 4.848 sec, 4.853 sec | SLOTPOWERLIMIT 1944516, ERR_COR 1945029 |
| G007 | 1944531 | C007, C025 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 485 | 4.848 sec, 4.853 sec | SLOTPOWERLIMIT 1944516, ERR_COR 1945029 |
| G008 | 1944533 | C008, C026 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 488 | 4.848 sec, 4.853 sec | SLOTPOWERLIMIT 1944516, ERR_COR 1945029 |
| G009 | 1944535 | C009, C027 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 148528 | 4.848 sec, 5.880 sec | ERR_COR 2093072 |
| G010 | 1944537 | C010, C028 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 148534 | 4.848 sec, 5.880 sec | ERR_COR 2093072 |
| G011 | 1944539 | C011, C029 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 148540 | 4.848 sec, 5.880 sec | ERR_COR 2093072 |
| G012 | 1944547 | C013, C031 | request_or_completion_is_other_candidate_anchor, shared_anchor_packet, shared_association_lineage | 148544 | 4.848 sec, 5.880 sec | ERR_COR 2093072 |
| G013 | 1944549 | C014 | none_singleton | 148973 | 4.848 sec | - |
| G014 | 1944553 | C016 | none_singleton | 148997 | 4.848 sec | - |
| G015 | 1944555 | C017 | none_singleton | 149009 | 4.848 sec | - |
| G016 | 1944557 | C018 | none_singleton | 149020 | 4.848 sec | - |

- 12 multi-member groups, 4 singletons (G013-G016: CfgRd0 same-key reappearances
  whose chains end at later CfgRd0 requests that are not candidates).
- The four 4.853 sec UR candidates stay in four groups (G005-G008): they are
  separate MRd(32) transactions, and same time, same status and the shared ERR_COR
  are auxiliary descriptors only. Likewise the five 5.880 sec UR candidates.

**G003** (Go to Packet 1944521):
- C003: CfgRd0 request 1944521 (Tag 0): same association key observed again at 1944543 (CfgRd0) before an associated completion was observed
- C012: CfgRd0 request 1944543 (Tag 0): same association key observed again at 1944567 (CfgWr0) before an associated completion was observed
- C021: CfgWr0 request 1944567 (Tag 0): same association key observed again at 2093086 (MRd(32)) before an associated completion was observed
- C030: MRd(32) request 2093086 (Tag 0) has associated completion 2093088 with status UR
**G005** (Go to Packet 1944525):
- C005: CfgRd0 request 1944525 (Tag 11): same association key observed again at 1945005 (MRd(32)) before an associated completion was observed
- C023: MRd(32) request 1945005 (Tag 11) has associated completion 1945008 with status UR

## Tension surfaced, not resolved here

Rule 2 follows the G2b reissue chain, and that chain can span the non-TLP stretch
of the capture. Groups ['G003', 'G009', 'G010', 'G011', 'G012'] join a 4.848 sec same-key reappearance with a
5.880 sec MRd(32) -> UR pair, with lineage spans of about 148,500 packets. This sits
next to the owner's separate guidance that the same Tag across a long packet gap
must not merge on its own. The rules were applied as fixed; whether rule 2 should
also be bounded by distance is an owner decision. Changing it now would be a
post-hoc adjustment and must be recorded as such. The span is visible per group.

## Limits

- One trace; ground truth UNKNOWN; grouping is by shared evidence, not by root cause.
- Nearby messages inherit G3c's prototype 64-packet heuristic.
- Structured findings for engineers are G3f.
