# PCIe-G2b Request/Completion Association — Evidence (2026-09-14)

Status: **G2b-1 PASS** (role classification) and **G2b-2 PASS** (request/completion
association) for 1350. This is association, not transaction reconstruction:
completeness, timeouts and faults are not evaluated. Ground truth remains UNKNOWN.

Offline step: input is the verified G2a canonical `fields.json`
(SHA-256 `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79`); PETracer was not opened.
Command: `python -X utf8 -B scripts/pcie/g2b_associate.py --fields artifacts/evidence/pcie-g2a-20260914/export/fields.json --output-dir artifacts/evidence/pcie-g2b-20260914`.

## Rules (owner decision 2026-09-14)

1. Only non-posted requests (MRd, MRdLk, IORd, IOWr, CfgRd0/1, CfgWr0/1, atomic
   operations) expect completions; MWr and Msg types are `POSTED_OR_OTHER`.
2. Candidate key `(RequesterId, Tag)`; a completion is associated with the
   nearest preceding non-posted request with the same key. `CompleterId`,
   `ComplStatus`, direction and packet gap are evidence, not key parts.
3. No one-to-one assumption: a completion never closes a request, so split
   completions accumulate on the same request.
4. No completeness claim (Byte Count / Length / Lower Address not read).
5. UR/CA/CRS are recorded as observations, not faults. A request with no
   completion before capture end is `NONE_OBSERVED_IN_CAPTURE`, never a timeout.
   If the same key is issued again before any completion was observed, the
   earlier request is `SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED` rather
   than guessed.

Type names come from the installed vendor constant table
`Scripts/VFScripts/VS_constants.inc SHA-256 799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D`. Codes `0x9` (CfgRd0), `0xE` (MsgD) and
`0x12` (CplD) are additionally GUI-confirmed on 1350 packets; `0x11` (Cpl) is
vendor-constant only and its rows are labelled `COMPLETION_CANDIDATE`.

## G2b-1 role classification

| Code | Vendor name | Evidence | Role | Rows |
| --- | --- | --- | --- | ---: |
| `0x1` | MRd(32) | VENDOR_CONSTANT | NON_POSTED_REQUEST | 82 |
| `0x3` | MWr(32) | VENDOR_CONSTANT | POSTED_OR_OTHER | 79 |
| `0x9` | CfgRd0 | GUI_CONFIRMED+VENDOR_CONSTANT | NON_POSTED_REQUEST | 293 |
| `0xA` | CfgWr0 | VENDOR_CONSTANT | NON_POSTED_REQUEST | 64 |
| `0xD` | Msg | VENDOR_CONSTANT | POSTED_OR_OTHER | 2 |
| `0xE` | MsgD | GUI_CONFIRMED+VENDOR_CONSTANT | POSTED_OR_OTHER | 1 |
| `0x11` | Cpl | VENDOR_CONSTANT | COMPLETION_CANDIDATE | 70 |
| `0x12` | CplD | GUI_CONFIRMED+VENDOR_CONSTANT | COMPLETION_CANDIDATE | 347 |

No row fell into `UNKNOWN`, and no field-shape inconsistency note was raised
(every completion type had CompleterId/ComplStatus; no request or posted type did).

## G2b-2 association

| Request type | Outcome | Requests |
| --- | --- | ---: |
| CfgRd0 | COMPLETIONS_OBSERVED | 274 |
| CfgRd0 | SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED | 19 |
| CfgWr0 | COMPLETIONS_OBSERVED | 61 |
| CfgWr0 | SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED | 3 |
| MRd(32) | COMPLETIONS_OBSERVED | 82 |

- 439 non-posted requests; 417 completion candidates,
  all associated (0 without a preceding request).
- Requests with more than one associated completion: 0.
- Direction relation of every association: {'opposite': 417}.
- `NONE_OBSERVED_IN_CAPTURE`: 0 requests.

GUI corroboration of one association: request 2097003 (CfgRd0, RequesterId
000:00.0, Tag 3) is associated with packet 2097005, two packets later. The
retained G1b screenshot `gui-row469-pkt-2097003.png` shows packet 2097005 as
TLP Cpl with RequesterID 000:0:0, Tag 3, CompleterID 001:00:0, Status SC,
matching the probe values (CplD, CompleterId 0x0100, ComplStatus 0).

### Completion status observations

| Completion type | Status | Completions |
| --- | --- | ---: |
| Cpl | SC | 61 |
| Cpl | UR | 9 |
| CplD | SC | 347 |

| Completion packet | Time | Type | Status | Associated request | Packet gap | Earlier same-key requests reissued before it |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1945008 | 4.853 sec | Cpl | UR | 1945005 (MRd(32), Tag 11) | 3 | 1 |
| 1945013 | 4.853 sec | Cpl | UR | 1945011 (MRd(32), Tag 1) | 2 | 2 |
| 1945018 | 4.853 sec | Cpl | UR | 1945016 (MRd(32), Tag 7) | 2 | 1 |
| 1945023 | 4.853 sec | Cpl | UR | 1945021 (MRd(32), Tag 13) | 2 | 1 |
| 2093065 | 5.880 sec | Cpl | UR | 2093063 (MRd(32), Tag 3) | 2 | 1 |
| 2093075 | 5.880 sec | Cpl | UR | 2093071 (MRd(32), Tag 9) | 4 | 1 |
| 2093081 | 5.880 sec | Cpl | UR | 2093079 (MRd(32), Tag 15) | 2 | 1 |
| 2093088 | 5.880 sec | Cpl | UR | 2093086 (MRd(32), Tag 0) | 2 | 3 |
| 2093093 | 5.880 sec | Cpl | UR | 2093091 (MRd(32), Tag 4) | 2 | 1 |

### Requests whose key was reissued before any completion was observed

22 requests (display times: {'4.848 sec': 22}).

| Request packet | Time | Type | Tag | Reissued by | Last request in the same-key chain | Its completion statuses |
| ---: | --- | --- | ---: | --- | ---: | --- |
| 1944517 | 4.848 sec | CfgRd0 | 8 | 1944559 (CfgRd0) | 2093601 | SC |
| 1944519 | 4.848 sec | CfgRd0 | 14 | 1944563 (CfgWr0) | 2093615 | SC |
| 1944521 | 4.848 sec | CfgRd0 | 0 | 1944543 (CfgRd0) | 2093086 | UR |
| 1944523 | 4.848 sec | CfgRd0 | 5 | 1944571 (CfgWr0) | 2093652 | SC |
| 1944525 | 4.848 sec | CfgRd0 | 11 | 1945005 (MRd(32)) | 1945005 | UR |
| 1944527 | 4.848 sec | CfgRd0 | 1 | 1944551 (CfgRd0) | 1945011 | UR |
| 1944531 | 4.848 sec | CfgRd0 | 7 | 1945016 (MRd(32)) | 1945016 | UR |
| 1944533 | 4.848 sec | CfgRd0 | 13 | 1945021 (MRd(32)) | 1945021 | UR |
| 1944535 | 4.848 sec | CfgRd0 | 3 | 2093063 (MRd(32)) | 2093063 | UR |
| 1944537 | 4.848 sec | CfgRd0 | 9 | 2093071 (MRd(32)) | 2093071 | UR |
| 1944539 | 4.848 sec | CfgRd0 | 15 | 2093079 (MRd(32)) | 2093079 | UR |
| 1944543 | 4.848 sec | CfgRd0 | 0 | 1944567 (CfgWr0) | 2093086 | UR |
| 1944547 | 4.848 sec | CfgRd0 | 4 | 2093091 (MRd(32)) | 2093091 | UR |
| 1944549 | 4.848 sec | CfgRd0 | 10 | 2093522 (CfgRd0) | 2093522 | SC |
| 1944551 | 4.848 sec | CfgRd0 | 1 | 1945011 (MRd(32)) | 1945011 | UR |
| 1944553 | 4.848 sec | CfgRd0 | 6 | 2093550 (CfgRd0) | 2093550 | SC |
| 1944555 | 4.848 sec | CfgRd0 | 12 | 2093564 (CfgRd0) | 2093564 | SC |
| 1944557 | 4.848 sec | CfgRd0 | 2 | 2093577 (CfgRd0) | 2093577 | SC |
| 1944559 | 4.848 sec | CfgRd0 | 8 | 2093601 (CfgRd0) | 2093601 | SC |
| 1944563 | 4.848 sec | CfgWr0 | 14 | 2093615 (CfgRd0) | 2093615 | SC |
| 1944567 | 4.848 sec | CfgWr0 | 0 | 2093086 (MRd(32)) | 2093086 | UR |
| 1944571 | 4.848 sec | CfgWr0 | 5 | 2093652 (CfgRd0) | 2093652 | SC |

These are descriptive only. The association rule cannot tell whether a later
completion answered the earlier or the later request of the same key, so no
claim is made that the earlier request went unanswered, timed out, or failed.
They, and the UR completions above, are inputs for G3 candidate review.

### Observations (descriptive, not findings)

- All 9 UR completions are associated with **MRd(32)** requests, not
  configuration requests: four around 4.853 sec and five around 5.880 sec,
  each 2-4 packets after its request.
- All 22 reissued-key requests occur at display time 4.848 sec, within the
  first TLPs of the capture: a CfgRd0 sequence cycling Tags 0-15 (plus three
  CfgWr0) for which no completion was observed before the same keys were used again.
- Association ambiguity check (resolved for two UR pairs, 13:30-13:33): the
  1350 G2a working copy was reopened read-only and the LeCroy trace view was
  switched to **Split** (split transactions). LeCroy's own grouping agrees with
  the G2b association:

  | G2b association | LeCroy split transaction | Link transactions inside | Evidence against an earlier same-key CfgRd0 |
  | --- | --- | --- | --- |
  | 1945005 MRd(32) Tag 11 -> 1945008 Cpl UR | Split Tra 22: MRd(32), RequesterID 000:0:0, CompleterID 001:0:0, Tag 11, Address 6C1FC028, Status UR, 2 link transactions | Link Tra 24 = MRd(32) packet 1945005 (ACK #1945006); Link Tra 25 = Cpl Tag 11, UR, Byte Cnt 8, Lwr Addr 0x028 (ACK #1945010) | Completion Lower Address 0x028 equals the MRd address low bits |
  | 2093086 MRd(32) Tag 0 -> 2093088 Cpl UR | Split Tra 29: MRd(32), RequesterID 000:0:0, CompleterID 001:0:0, Tag 0, Address 6C1FC01C, Status UR, 2 link transactions | Link Tra 42 = MRd(32) packet 2093086 (ACK #2093087); Link Tra 43 = Cpl Tag 0, UR, Byte Cnt 4, Lwr Addr 0x01C (ACK #2093090) | Completion Lower Address 0x01C equals the MRd address low bits |

  The collapsed completion rows do not print their own packet number; 1945008
  and 2093088 are identified by the probe's tag/status values, time stamps and
  the adjacent explicit ACK packet numbers. The same screens also show LeCroy
  split transactions pairing MRd(32) with UR for Tags 1, 7, 13 (Split Tra 23-25)
  and Tag 4 (Split Tra 30), matching the other G2b UR associations, and a Link
  Tra 41 Cpl Tag 15 UR (Lwr Addr 0x01C) consistent with 2093079 -> 2093081.
  Screenshots in `artifacts/evidence/pcie-g2b-20260914/gui-split/`:
  `split-view-pkt-1945000.png` (SHA-256 `21C3BC2C159504AA024057CC70C9321F2DE2C82D810F4C1DDF9B66344FA06466`),
  `split-view-pkt-1945005.png` (`70E1127F398C5EF97A0D7E9BE596A9D1D3DFC7B5AA42A649028CA563A06C705A`),
  `split-view-pkt-2093080.png` (`78314A1743050828A58CAB7DC61973C38B8D2828B2B6D600BA0672224A94BBBD`),
  `split-view-pkt-2093086.png` (`E8E5F89C114AD67CEF710CEF0345F5E609F741EE46ABD43413B9B9F9658580DA`).
  Post-close integrity at 13:33:03 +08:00: source trace, working copy and
  PETracer executable unchanged.
- Also visible (descriptive only): Link Tra 33, a Msg routed To RC with Message
  Code ERR_COR from RequesterID 001:0:0, shortly after the 4.853 sec UR group;
  it corresponds to the G2a `0xD` Msg rows with RequesterId 0x0100.
- Not GUI-checked: the 22 reissued-key requests at 4.848 sec.

## Outputs (`artifacts/evidence/pcie-g2b-20260914/`)

| File | SHA-256 |
| --- | --- |
| roles.json | `556F9F838F1E0295CF6B71EA00B9DD5C2C82A9CC0D7964F202F63BC29A76F7B8` |
| associations.json | `BDF7D1C20A4948E2497FC6C8F4A8AE6A5491D9CE9D1D162365C3696B41139A12` |
| orphan_completions.json | `37517E5F3DC66819F61F5A7BB8ACE1921282415F10551D2DEFA5C3EB0985B570` |

`associations.tsv` and `summary.json` are derived views of the same data.

## Not established

- transaction completeness (Byte Count / Length / Lower Address not read)
- completion timeout: no completion observed before capture end is not a protocol timeout
- fault or abnormality: UR/CA/CRS status values are observations only
- correctness of nearest-preceding association when Tags are reused, beyond the GUI-checked UR pairs
- GUI name of vendor code `0x11`.
