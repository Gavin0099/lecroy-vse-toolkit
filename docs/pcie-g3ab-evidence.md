# PCIe-G3a / G3b Candidate Detectors — Evidence (2026-09-14)

Status: **G3a PASS (prototype)** and **G3b PASS (prototype)** for 1350. These
detectors surface *candidates*: places an engineer may want to look at. They do
not classify anomalies, faults, retries or timeouts, and they do not rank or
group. Every candidate carries `interpretation: NOT_EVALUATED`. Ground truth
for 1350 remains UNKNOWN.

Offline step (PETracer not opened):

```text
python -X utf8 -B scripts/pcie/g3_candidates.py   --associations artifacts/evidence/pcie-g2b-20260914/associations.json   --gui-crosschecks artifacts/evidence/pcie-g2b-20260914/gui-split/crosschecks.json   --output-dir artifacts/evidence/pcie-g3-20260914
```

| Input / output | SHA-256 |
| --- | --- |
| G2b associations.json | `BDF7D1C20A4948E2497FC6C8F4A8AE6A5491D9CE9D1D162365C3696B41139A12` |
| GUI cross-check record | `151FEBC497C4311C44C33D5EA3B08504429FDE0B783500C52E2412518C49940A` |
| candidates.json | `290FDE9569356CBE73B21735AF261DCC59FB5EBC4563E4A87DE12ECF4C2F181E` |
| candidates.tsv | `2B68C917D45C17370D899650684821EBDE93E4A472CFBB7836367689B37A731F` |

## Detector definitions

| Detector | Surfaces | Does not establish |
| --- | --- | --- |
| `G3A_NON_SUCCESS_COMPLETION` | An associated completion reports a status other than SC. | that the request was invalid or the device misbehaved (UR can be expected, e.g. probing absent functions); a causal link to any user-visible failure; that the association is correct when earlier same-key requests were reissued, unless GUI-cross-checked |
| `G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION` | Same association key observed again before an associated completion was observed in the captured sequence. | that the requester retransmitted the request; that this is not an analyzer or capture representation effect; that the Tag reuse is protocol-illegal; that the earlier request's completion did not occur outside the capture |

Candidate IDs follow capture order of the anchor packet (G3a anchors on the
completion, G3b on the first request). A unit test fails if candidate text
contains "fault", "timeout", "retry error", "anomaly" or "root cause"; the 1350
output contains none of them.

## G3a — non-success completion candidates (9)

| ID | Time | Request | Completion | Earlier same-key requests reissued into this request | GUI cross-check | Interpretation |
| --- | --- | --- | --- | ---: | --- | --- |
| C023 | 4.853 sec | 1945005 MRd(32) Tag 11 | 1945008 Cpl UR (gap 3) | 1 | MATCHED (Split Tra 22) | NOT_EVALUATED |
| C024 | 4.853 sec | 1945011 MRd(32) Tag 1 | 1945013 Cpl UR (gap 2) | 2 | - | NOT_EVALUATED |
| C025 | 4.853 sec | 1945016 MRd(32) Tag 7 | 1945018 Cpl UR (gap 2) | 1 | - | NOT_EVALUATED |
| C026 | 4.853 sec | 1945021 MRd(32) Tag 13 | 1945023 Cpl UR (gap 2) | 1 | - | NOT_EVALUATED |
| C027 | 5.880 sec | 2093063 MRd(32) Tag 3 | 2093065 Cpl UR (gap 2) | 1 | - | NOT_EVALUATED |
| C028 | 5.880 sec | 2093071 MRd(32) Tag 9 | 2093075 Cpl UR (gap 4) | 1 | - | NOT_EVALUATED |
| C029 | 5.880 sec | 2093079 MRd(32) Tag 15 | 2093081 Cpl UR (gap 2) | 1 | - | NOT_EVALUATED |
| C030 | 5.880 sec | 2093086 MRd(32) Tag 0 | 2093088 Cpl UR (gap 2) | 3 | MATCHED (Split Tra 29) | NOT_EVALUATED |
| C031 | 5.880 sec | 2093091 MRd(32) Tag 4 | 2093093 Cpl UR (gap 2) | 1 | - | NOT_EVALUATED |

C023 and C030 carry the LeCroy Split transaction cross-check (Split Tra 22 and
29, completion Lower Address matching the MRd address low bits). The other seven
rely on the G2b association rule; LeCroy screens showed consistent MRd(32)+UR
split transactions for several of them, but they are not recorded as formal
cross-checks.

## G3b — same key reappeared before completion (22)

| ID | First request | Tag | Reappeared as | Packet gap | Completion observed later for same key | Later completion (attributed request) | Interpretation |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| C001 | 1944517 CfgRd0 | 8 | 1944559 CfgRd0 (4.848 sec) | 42 | YES | 2093603 SC at 5.883 sec (request 2093601) | NOT_EVALUATED |
| C002 | 1944519 CfgRd0 | 14 | 1944563 CfgWr0 (4.848 sec) | 44 | YES | 2093617 SC at 5.883 sec (request 2093615) | NOT_EVALUATED |
| C003 | 1944521 CfgRd0 | 0 | 1944543 CfgRd0 (4.848 sec) | 22 | YES | 2093088 UR at 5.880 sec (request 2093086) | NOT_EVALUATED |
| C004 | 1944523 CfgRd0 | 5 | 1944571 CfgWr0 (4.848 sec) | 48 | YES | 2093654 SC at 5.883 sec (request 2093652) | NOT_EVALUATED |
| C005 | 1944525 CfgRd0 | 11 | 1945005 MRd(32) (4.853 sec) | 480 | YES | 1945008 UR at 4.853 sec (request 1945005) | NOT_EVALUATED |
| C006 | 1944527 CfgRd0 | 1 | 1944551 CfgRd0 (4.848 sec) | 24 | YES | 1945013 UR at 4.853 sec (request 1945011) | NOT_EVALUATED |
| C007 | 1944531 CfgRd0 | 7 | 1945016 MRd(32) (4.853 sec) | 485 | YES | 1945018 UR at 4.853 sec (request 1945016) | NOT_EVALUATED |
| C008 | 1944533 CfgRd0 | 13 | 1945021 MRd(32) (4.853 sec) | 488 | YES | 1945023 UR at 4.853 sec (request 1945021) | NOT_EVALUATED |
| C009 | 1944535 CfgRd0 | 3 | 2093063 MRd(32) (5.880 sec) | 148528 | YES | 2093065 UR at 5.880 sec (request 2093063) | NOT_EVALUATED |
| C010 | 1944537 CfgRd0 | 9 | 2093071 MRd(32) (5.880 sec) | 148534 | YES | 2093075 UR at 5.880 sec (request 2093071) | NOT_EVALUATED |
| C011 | 1944539 CfgRd0 | 15 | 2093079 MRd(32) (5.880 sec) | 148540 | YES | 2093081 UR at 5.880 sec (request 2093079) | NOT_EVALUATED |
| C012 | 1944543 CfgRd0 | 0 | 1944567 CfgWr0 (4.848 sec) | 24 | YES | 2093088 UR at 5.880 sec (request 2093086) | NOT_EVALUATED |
| C013 | 1944547 CfgRd0 | 4 | 2093091 MRd(32) (5.880 sec) | 148544 | YES | 2093093 UR at 5.880 sec (request 2093091) | NOT_EVALUATED |
| C014 | 1944549 CfgRd0 | 10 | 2093522 CfgRd0 (5.883 sec) | 148973 | YES | 2093524 SC at 5.883 sec (request 2093522) | NOT_EVALUATED |
| C015 | 1944551 CfgRd0 | 1 | 1945011 MRd(32) (4.853 sec) | 460 | YES | 1945013 UR at 4.853 sec (request 1945011) | NOT_EVALUATED |
| C016 | 1944553 CfgRd0 | 6 | 2093550 CfgRd0 (5.883 sec) | 148997 | YES | 2093552 SC at 5.883 sec (request 2093550) | NOT_EVALUATED |
| C017 | 1944555 CfgRd0 | 12 | 2093564 CfgRd0 (5.883 sec) | 149009 | YES | 2093566 SC at 5.883 sec (request 2093564) | NOT_EVALUATED |
| C018 | 1944557 CfgRd0 | 2 | 2093577 CfgRd0 (5.883 sec) | 149020 | YES | 2093580 SC at 5.883 sec (request 2093577) | NOT_EVALUATED |
| C019 | 1944559 CfgRd0 | 8 | 2093601 CfgRd0 (5.883 sec) | 149042 | YES | 2093603 SC at 5.883 sec (request 2093601) | NOT_EVALUATED |
| C020 | 1944563 CfgWr0 | 14 | 2093615 CfgRd0 (5.883 sec) | 149052 | YES | 2093617 SC at 5.883 sec (request 2093615) | NOT_EVALUATED |
| C021 | 1944567 CfgWr0 | 0 | 2093086 MRd(32) (5.880 sec) | 148519 | YES | 2093088 UR at 5.880 sec (request 2093086) | NOT_EVALUATED |
| C022 | 1944571 CfgWr0 | 5 | 2093652 CfgRd0 (5.883 sec) | 149081 | YES | 2093654 SC at 5.883 sec (request 2093652) | NOT_EVALUATED |

Descriptive properties, relevant to how an engineer would read these:

- Type relation between first and reappearing request: {'same type': 8, 'CfgRd0 -> CfgWr0': 3, 'CfgRd0 -> MRd(32)': 8, 'CfgWr0 -> CfgRd0': 2, 'CfgWr0 -> MRd(32)': 1}.
  When the key reappears on a different request type (for example CfgRd0 then
  MRd(32)), the pattern reads more like Tag reuse for a new request than a
  resend of the same request; the detector does not decide which.
- `completion_observed_later_for_same_key` is YES for all 22, but the later
  completion is attributed to the *last* request of the same-key chain, not to
  the first request, and often appears much later: display times {'5.883 sec': 10, '5.880 sec': 7, '4.853 sec': 5};
  statuses {'SC': 10, 'UR': 12}. YES therefore does not mean the first request
  was answered, or answered promptly.
- All 22 first requests are at display time 4.848 sec, within the first TLPs of
  the capture.

## Not established

- Whether any candidate relates to the failure the trace was captured for.
- Grouping, context windows, nearby error messages (ERR_COR) and ranking
  (G3c-G3e); structured findings for reports (G3f).
- GUI confirmation of the 22 G3b first requests and of seven G3a pairs.
