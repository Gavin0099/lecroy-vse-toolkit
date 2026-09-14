# PCIe-G3d Candidate Context Windows — Evidence (2026-09-14)

Status: **G3d PASS (prototype)** for 1350. Every G3a/G3b candidate gets a primary
LeCroy Go to Packet position and bounded TLP context before, at and after its
anchors. Presentation only: no new candidates, no ranking, no interpretation
(`interpretation: NOT_EVALUATED`). PETracer was not opened.

## Inputs and output

| Input | Path | SHA-256 |
| --- | --- | --- |
| fields | `artifacts/evidence/pcie-g2a-20260914/export/fields.json` | `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79` |
| roles | `artifacts/evidence/pcie-g2b-20260914/roles.json` | `556F9F838F1E0295CF6B71EA00B9DD5C2C82A9CC0D7964F202F63BC29A76F7B8` |
| associations | `artifacts/evidence/pcie-g2b-20260914/associations.json` | `BDF7D1C20A4948E2497FC6C8F4A8AE6A5491D9CE9D1D162365C3696B41139A12` |
| candidates | `artifacts/evidence/pcie-g3-20260914/candidates.json` | `290FDE9569356CBE73B21735AF261DCC59FB5EBC4563E4A87DE12ECF4C2F181E` |
| nearby | `artifacts/evidence/pcie-g3c-20260914/nearby_messages.json` | `9E9AC2EF885687356ADE17D6DB79A7D33475ECD7BA0078FE730B0A811D608EF3` |

Output `artifacts/evidence/pcie-g3d-20260914/contexts.json`, SHA-256 `8C3D00FFEF860F44D171A9E96437D3F36EB4A760B9E075AF6818C323A280D74D`.

```text
python -X utf8 -B scripts/pcie/g3d_context.py   --fields artifacts/evidence/pcie-g2a-20260914/export/fields.json   --roles artifacts/evidence/pcie-g2b-20260914/roles.json   --associations artifacts/evidence/pcie-g2b-20260914/associations.json   --candidates artifacts/evidence/pcie-g3-20260914/candidates.json   --nearby artifacts/evidence/pcie-g3c-20260914/nearby_messages.json   --context-rows 5 --output-dir artifacts/evidence/pcie-g3d-20260914
```

## Structure per candidate

- `candidate_anchor`: `primary_goto_packet` (G3a: request; G3b: first request),
  `secondary_packet` (G3a: completion; G3b: repeated request), and a LeCroy hint
  (Search > Go to Packet, Ctrl+G; the trace view also shows non-TLP packets).
- `context_blocks`: G3a has one block (request..completion span); G3b has two
  (first request, repeated request), because the two can be far apart.
  Each block has `before`, `anchor` and `after` rows.
- Every row keeps packet index, **raw packet gap from the previous TLP row**,
  display time, channel, vendor type name, role, RequesterId, Tag, CompleterId,
  completion status, G2b association, markers (`ANCHOR_*`,
  `NEARBY_MESSAGE_G3C`) and `also_anchor_of_candidates` (cross-reference only).
- `nearby_messages_from_g3c` and `nearby_messages_excluded_by_g3c_bound` are
  copied from G3c, not recomputed.

## Context size (explicit heuristic)

5 TLP rows before and after each anchor span, status `PRESENTATION_HEURISTIC`.
Rows are TLPs only; DLLPs and other packets between them are visible in LeCroy.
When fewer rows exist, the side is marked `TRUNCATED_AT_CAPTURE_BOUNDARY`.

Result: 31 candidates, 53 context blocks,
4 truncated sides: [('C001', 'first_request', 'before'), ('C002', 'first_request', 'before'), ('C003', 'first_request', 'before'), ('C004', 'first_request', 'before')].

The per-row packet gap was added before delivery after the first run showed
context rows spanning non-TLP stretches without any visible signal. It is a raw
number with no threshold. Context rows preceded by more than 1000 packets
(descriptive): [('C008', 'repeated_request', 2093063, 148034), ('C009', 'repeated_request', 2093063, 148034), ('C010', 'repeated_request', 2093063, 148034), ('C025', 'request_to_completion', 2093063, 148034), ('C026', 'request_to_completion', 2093063, 148034), ('C027', 'request_to_completion', 2093063, 148034), ('C028', 'request_to_completion', 2093063, 148034)]. These are the rows where a block crosses from the
4.853 sec group to the 5.880 sec group.

## Example: C023 (G3a, MRd(32) -> UR, GUI-cross-checked pair)

Primary Go to Packet **1945005**, secondary 1945008. Nearby messages from G3c: 1945029 ERR_COR (after).

| Part | Packet | Gap from previous TLP | Time | Channel | Type | Requester | Tag | Completer | Status | Markers |
| --- | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- | --- |
| before | 1944559 | 2 | 4.848 sec | Downstream | CfgRd0 | 000:00.0 | 8 | - | - | - |
| before | 1944563 | 4 | 4.848 sec | Downstream | CfgWr0 | 000:00.0 | 14 | - | - | - |
| before | 1944567 | 4 | 4.848 sec | Downstream | CfgWr0 | 000:00.0 | 0 | - | - | - |
| before | 1944571 | 4 | 4.848 sec | Downstream | CfgWr0 | 000:00.0 | 5 | - | - | - |
| before | 1945003 | 432 | 4.853 sec | Downstream | MWr(32) | 000:00.0 | 0 | - | - | - |
| anchor | 1945005 | 2 | 4.853 sec | Downstream | MRd(32) | 000:00.0 | 11 | - | - | ANCHOR_REQUEST |
| anchor | 1945008 | 3 | 4.853 sec | Upstream | Cpl | 000:00.0 | 11 | 001:00.0 | UR | ANCHOR_COMPLETION |
| after | 1945011 | 3 | 4.853 sec | Downstream | MRd(32) | 000:00.0 | 1 | - | - | - |
| after | 1945013 | 2 | 4.853 sec | Upstream | Cpl | 000:00.0 | 1 | 001:00.0 | UR | - |
| after | 1945016 | 3 | 4.853 sec | Downstream | MRd(32) | 000:00.0 | 7 | - | - | - |
| after | 1945018 | 2 | 4.853 sec | Upstream | Cpl | 000:00.0 | 7 | 001:00.0 | UR | - |
| after | 1945021 | 3 | 4.853 sec | Downstream | MRd(32) | 000:00.0 | 13 | - | - | - |

## Example: C030 (G3a, MRd(32) -> UR, GUI-cross-checked pair)

Primary Go to Packet **2093086**, secondary 2093088. Nearby messages from G3c: 2093072 ERR_COR (before).

| Part | Packet | Gap from previous TLP | Time | Channel | Type | Requester | Tag | Completer | Status | Markers |
| --- | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- | --- |
| before | 2093071 | 3 | 5.880 sec | Downstream | MRd(32) | 000:00.0 | 9 | - | - | - |
| before | 2093072 | 1 | 5.880 sec | Upstream | Msg | 001:00.0 | 0 | - | - | NEARBY_MESSAGE_G3C |
| before | 2093075 | 3 | 5.880 sec | Upstream | Cpl | 000:00.0 | 9 | 001:00.0 | UR | - |
| before | 2093079 | 4 | 5.880 sec | Downstream | MRd(32) | 000:00.0 | 15 | - | - | - |
| before | 2093081 | 2 | 5.880 sec | Upstream | Cpl | 000:00.0 | 15 | 001:00.0 | UR | - |
| anchor | 2093086 | 5 | 5.880 sec | Downstream | MRd(32) | 000:00.0 | 0 | - | - | ANCHOR_REQUEST |
| anchor | 2093088 | 2 | 5.880 sec | Upstream | Cpl | 000:00.0 | 0 | 001:00.0 | UR | ANCHOR_COMPLETION |
| after | 2093091 | 3 | 5.880 sec | Downstream | MRd(32) | 000:00.0 | 4 | - | - | - |
| after | 2093093 | 2 | 5.880 sec | Upstream | Cpl | 000:00.0 | 4 | 001:00.0 | UR | - |
| after | 2093522 | 429 | 5.883 sec | Downstream | CfgRd0 | 000:00.0 | 10 | - | - | - |
| after | 2093524 | 2 | 5.883 sec | Upstream | CplD | 000:00.0 | 10 | 001:00.0 | SC | - |
| after | 2093536 | 12 | 5.883 sec | Downstream | CfgRd0 | 000:00.0 | 1 | - | - | - |

## Limits

- Context size (5 rows) is a presentation heuristic, not an analysis rule.
- Nearby messages inherit G3c's 64-packet bound, a prototype heuristic chosen
  after seeing G3c v1 results; not a proven PCIe rule.
- Neighbouring rows are listed for navigation; being in a context window does
  not mean a row is related to the candidate.
- One trace; ground truth UNKNOWN; grouping of overlapping candidates is G3e.
