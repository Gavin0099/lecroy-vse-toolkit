# PCIe-G3c Nearby Message Correlation — Evidence (2026-09-14)

Status: **G3c PASS (prototype)** for 1350. Each G3a/G3b candidate is annotated
with Message TLPs inside a fixed, non-timestamp window. Every attachment has
`relationship: temporal_correlation_only`; every candidate keeps
`interpretation: NOT_EVALUATED`. Causality between any candidate and any
message is NOT ESTABLISHED. G3a/G3b outputs were not modified. PETracer was not opened.

## Inputs and output

| Item | SHA-256 |
| --- | --- |
| G3 candidates.json | `290FDE9569356CBE73B21735AF261DCC59FB5EBC4563E4A87DE12ECF4C2F181E` |
| G2a fields.json | `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79` |
| G3c-0 messages.json | `08A7307F029E2BB55EC9419EE694ED97EAA1518112AC1C9E288E2AE9D57E1754` |
| **nearby_messages.json (v2)** | `9E9AC2EF885687356ADE17D6DB79A7D33475ECD7BA0078FE730B0A811D608EF3` |
| nearby_messages.json (v1, rows only, superseded) | `1EA4315E9FFF24225772ABA4B86CD2540C0782ECF85253573A47D3D58B676ABC` |

```text
python -X utf8 -B scripts/pcie/g3c_nearby_messages.py   --candidates artifacts/evidence/pcie-g3-20260914/candidates.json   --fields artifacts/evidence/pcie-g2a-20260914/export/fields.json   --messages artifacts/evidence/pcie-g3c0-20260914/export/messages.json   --window 8 --max-packet-gap 64 --output-dir artifacts/evidence/pcie-g3c-20260914
```

## Window definition

- **TLP rows**: a message is considered only if its row in the 938-row G2a TLP
  export is within 8 rows of the candidate's anchor span. G3a anchor span is
  request..completion; G3b searches the first request and the reappearing
  request as two separate spans.
- **Vendor packet-index distance**: the message must also be within 64 vendor
  packet indices of the nearest anchor packet.
- No timestamp is used; display time is millisecond text only.

`tlp_row_gap` and `packet_gap` are reported relative to the nearest anchor
packet; `position` is before, after, or inside the anchor span.

### Why v2 added the packet bound (disclosed correction)

v1 used the TLP-row window alone (N = 8, fixed before looking at results). Its
output attached ERR_COR messages that were row-adjacent but about 148,000
vendor packets away, because 1350 has no TLPs between the 4.853 sec and
5.880 sec groups. Row adjacency across that stretch is not nearness, so v2
adds the packet-distance bound. The value 64 was chosen **after** seeing v1;
it separates the within-group distances (at most 21 packets) from the
cross-gap ones (148,034-148,051). It also excludes one pair at -450 packets
(C014 to 2093072), a consequence of the chosen bound rather than of the data.
Excluded pairs remain listed per candidate in `excluded_beyond_packet_bound`.
The v1 output is kept, unmodified, as
`artifacts/evidence/pcie-g3c-20260914-v1-rowonly/`.

## Result (v2)

- Candidates with at least one nearby message: 23 of 31.
- Attachments excluded by the packet bound: 9.
- Messages not near any candidate: 0.

| ID | Detector | Candidate packet | Time | Nearby messages (temporal correlation only) | Excluded beyond packet bound |
| --- | --- | ---: | --- | --- | --- |
| C001 | G3b | 1944517 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -1, packets -1, anchor first_request) | - |
| C002 | G3b | 1944519 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -2, packets -3, anchor first_request) | - |
| C003 | G3b | 1944521 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -3, packets -5, anchor first_request) | - |
| C004 | G3b | 1944523 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -4, packets -7, anchor first_request) | - |
| C005 | G3b | 1944525 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -5, packets -9, anchor first_request) | - |
| C006 | G3b | 1944527 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -6, packets -11, anchor first_request) | - |
| C007 | G3b | 1944531 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -7, packets -15, anchor first_request)<br>1945029 ERR_COR (TOROOTCOMPLEX, after, rows +5, packets +13, anchor repeated_request) | - |
| C008 | G3b | 1944533 | 4.848 sec | 1944516 SLOTPOWERLIMIT (LOCALTERMRECEIVER, before, rows -8, packets -17, anchor first_request)<br>1945029 ERR_COR (TOROOTCOMPLEX, after, rows +3, packets +8, anchor repeated_request) | 2093072 ERR_COR (rows +8, packets +148051) |
| C009 | G3b | 1944535 | 4.848 sec | 2093072 ERR_COR (TOROOTCOMPLEX, after, rows +4, packets +9, anchor repeated_request) | 1945029 ERR_COR (rows -1, packets -148034) |
| C010 | G3b | 1944537 | 4.848 sec | 2093072 ERR_COR (TOROOTCOMPLEX, after, rows +1, packets +1, anchor repeated_request) | 1945029 ERR_COR (rows -4, packets -148042) |
| C011 | G3b | 1944539 | 4.848 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -2, packets -7, anchor repeated_request) | 1945029 ERR_COR (rows -7, packets -148050) |
| C012 | G3b | 1944543 | 4.848 sec | - | - |
| C013 | G3b | 1944547 | 4.848 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -6, packets -19, anchor repeated_request) | - |
| C014 | G3b | 1944549 | 4.848 sec | - | 2093072 ERR_COR (rows -8, packets -450) |
| C015 | G3b | 1944551 | 4.848 sec | 1945029 ERR_COR (TOROOTCOMPLEX, after, rows +7, packets +18, anchor repeated_request) | - |
| C016 | G3b | 1944553 | 4.848 sec | - | - |
| C017 | G3b | 1944555 | 4.848 sec | - | - |
| C018 | G3b | 1944557 | 4.848 sec | - | - |
| C019 | G3b | 1944559 | 4.848 sec | - | - |
| C020 | G3b | 1944563 | 4.848 sec | - | - |
| C021 | G3b | 1944567 | 4.848 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -4, packets -14, anchor repeated_request) | - |
| C022 | G3b | 1944571 | 4.848 sec | - | - |
| C023 | G3a | 1945008 | 4.853 sec | 1945029 ERR_COR (TOROOTCOMPLEX, after, rows +8, packets +21, anchor request/completion) | - |
| C024 | G3a | 1945013 | 4.853 sec | 1945029 ERR_COR (TOROOTCOMPLEX, after, rows +6, packets +16, anchor request/completion) | - |
| C025 | G3a | 1945018 | 4.853 sec | 1945029 ERR_COR (TOROOTCOMPLEX, after, rows +4, packets +11, anchor request/completion) | - |
| C026 | G3a | 1945023 | 4.853 sec | 1945029 ERR_COR (TOROOTCOMPLEX, after, rows +2, packets +6, anchor request/completion) | 2093072 ERR_COR (rows +7, packets +148049) |
| C027 | G3a | 2093065 | 5.880 sec | 2093072 ERR_COR (TOROOTCOMPLEX, after, rows +3, packets +7, anchor request/completion) | 1945029 ERR_COR (rows -1, packets -148034) |
| C028 | G3a | 2093075 | 5.880 sec | 2093072 ERR_COR (TOROOTCOMPLEX, inside_anchor_span, rows +0, packets +1, anchor request/completion) | 1945029 ERR_COR (rows -4, packets -148042) |
| C029 | G3a | 2093081 | 5.880 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -2, packets -7, anchor request/completion) | 1945029 ERR_COR (rows -7, packets -148050) |
| C030 | G3a | 2093088 | 5.880 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -4, packets -14, anchor request/completion) | - |
| C031 | G3a | 2093093 | 5.880 sec | 2093072 ERR_COR (TOROOTCOMPLEX, before, rows -6, packets -19, anchor request/completion) | - |

## Descriptive observations (not findings)

- Each of the nine G3a UR candidates has exactly one nearby ERR_COR, and it is
  the one from its own time group: C023-C026 with 1945029 (6-21 packets after
  the completion), C027-C031 with 2093072.
- For C028 the ERR_COR 2093072 lies inside the anchor span, between request
  2093071 and its UR completion 2093075.
- The G3b candidates at 4.848 sec see the MsgD SLOTPOWERLIMIT (1944516) just
  before their first requests; that message precedes the capture's first
  CfgRd0 sequence. G3b candidates whose repeated request falls in a UR group
  see that group's ERR_COR.
- None of these adjacencies is evidence that one event produced another.

## Not established

- **Prototype heuristic (risk kept, owner note 2026-09-14):** the 64-packet bound was
  selected after seeing v1 results. It is a prototype heuristic for 1350, not a proven
  PCIe rule, and any report built on G3c must state this limit.
- Causal relation between UR completions, reappeared keys and ERR_COR messages.
- Whether the window bounds (8 rows, 64 packets) generalize beyond 1350.
- GUI confirmation of 2093072's message code (1945029 is GUI-matched in G3c-0).
