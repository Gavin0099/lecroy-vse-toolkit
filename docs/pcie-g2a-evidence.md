# PCIe-G2a Transaction Field Probe — Evidence (2026-09-14)

Status: **PASS** — VSE exposes `in.Tag`, `in.RequesterId`, `in.CompleterId` and
`in.ComplStatus` on 1350, with values equal to the GUI for one request and one
completion. Not request/completion pairing (G2b), not anomaly detection, not a
diagnosis; ground truth remains UNKNOWN.

## Inputs

| Item | Identity |
| --- | --- |
| Source trace | `S0-Remove SD7-1350.pex`, SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Working copy | `C:\Users\reiko\AppData\Local\Temp\pcie-g2a-20260914-d2b3a003\S0-Remove SD7-1350.pex`, identical identity, ReadOnly |
| Analyzer | PETracer 13.26 (Build 43) BETA, SHA-256 `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| Script | `scripts/pcie/g2a-tlp-fields.pevs`, repo and deployed SHA-256 `DBE5ADB6AC4CD02FF73B013C69B5296D6262A7ED835ECADEBE0FA798E3C726FE` |
| G1 references | G1a log SHA-256 `C1B551461F30FD5FE863DE8BF0B95DE68F7028A6972DDCA0F1DDE99E14A17A39`; G1 canonical rows.json SHA-256 `A5398FB6863F63CC44D809EFF2884E3EECE53D551B1FCA18414238C5EE0C12D6` |

The probe reads each field only through a `!= null` guard (vendor idiom) and
prints `NA` for null; no default is substituted.

## Execution

Same guarded GUI sequence as G1b/G1d. The first attempt at 13:11:54 stopped
before Run because the estimated list position selected `p0-c1-message` and
its description did not match; PETracer was closed without running a script.
The list position was corrected from a screenshot (59 items; `g2a-tlp-fields`
is index 53).

13:14:44 loaded, 13:14:52.851 Run requested, DONE observed 2.0 s later,
13:14:57 log saved, 13:15:14 PETracer exited.

## Output and verification

Log `artifacts/evidence/pcie-g2a-20260914/g2a-tlp-fields.log.txt`, 61875 bytes,
SHA-256 `FA7A93EF0B61DBA9D9E2FF3CDF8212C4910F63A987A4397ED269C09DD1DFCA72`.
No error text; one `PCIE_G2A_END|rows=938|reason=trace_end`; DONE present.

`verify_g2a_fields.py` returned `PASS_FIELD_PROBE_OUTPUT`: 938 rows whose index,
display time, channel and type code equal the verified G1 export row by row.
fields.tsv SHA-256 `0D759B8EEE1B0F5D896DDCFD9893369E932E9A119FD0189B1876175885384732`, canonical fields.json
SHA-256 `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79`.

## GUI agreement (retained G1b GUI screenshots of the same trace identity)

| Packet | GUI (screenshot) | VSE probe | Result |
| --- | --- | --- | --- |
| 2097003 (request) | TLP Cfg / CfgRd0; RequesterID 000:0:0; Tag 3; DeviceID 001:00:0; no CompleterID/Status fields shown (`gui-row469-pkt-2097003.png`) | type `0x9`; Tag 3; RequesterId 0x0000 (000:00.0); CompleterId NA; ComplStatus NA | MATCHED |
| 2121703 (completion) | TLP Cpl / CplD; RequesterID 000:0:0; Tag 7; CompleterID 001:00:0; Status SC (`gui-row938-pkt-2121703.png`) | type `0x12`; Tag 7; RequesterId 0x0000; CompleterId 0x0100 (001:00.0); ComplStatus 0 (SC) | MATCHED |

Routing IDs are decoded as bus = id >> 8, device = (id >> 3) & 0x1F,
function = id & 7. Status name for 0 follows the vendor compliance constant
`CS_SUCCESSFUL_COMPLETION = 0`.

## Field availability by vendor TLP type code (present / rows)

| Type | Rows | Tag | RequesterId | CompleterId | ComplStatus |
| --- | ---: | --- | --- | --- | --- |
| `0x1` | 82 | 82/82 (16 distinct) | 82/82 (1 distinct) | 0/82 | 0/82 |
| `0x3` | 79 | 79/79 (1 distinct) | 79/79 (1 distinct) | 0/79 | 0/79 |
| `0x9` | 293 | 293/293 (16 distinct) | 293/293 (1 distinct) | 0/293 | 0/293 |
| `0xA` | 64 | 64/64 (16 distinct) | 64/64 (1 distinct) | 0/64 | 0/64 |
| `0xD` | 2 | 2/2 (1 distinct) | 2/2 (1 distinct) | 0/2 | 0/2 |
| `0xE` | 1 | 1/1 (1 distinct) | 1/1 (1 distinct) | 0/1 | 0/1 |
| `0x11` | 70 | 70/70 (16 distinct) | 70/70 (1 distinct) | 70/70 (1 distinct) | 70/70 (2 distinct) |
| `0x12` | 347 | 347/347 (16 distinct) | 347/347 (1 distinct) | 347/347 (1 distinct) | 347/347 (1 distinct) |

Observations for the G2b data model:

- `CompleterId` and `ComplStatus` read null on every non-completion type seen
  and non-null only on `0x11` and `0x12`. For these two fields null does
  separate applicability on this trace.
- `Tag` and `RequesterId` are never null, including on type `0xE` (GUI: Msg /
  MsgD). A non-null value therefore does not prove the field is meaningful for
  that TLP type; G2b must choose pairing keys per TLP type, not from nullness.
- Only `0x12` is GUI-confirmed as CplD. `0x11` is inferred to be a completion
  type only from its field availability; its vendor name is not yet GUI-observed.

## Completion status values (descriptive, not a finding)

| Type | ComplStatus | Rows |
| --- | ---: | ---: |
| `0x11` | 0 | 61 |
| `0x11` | 1 | 9 |
| `0x12` | 0 | 347 |

Rows with ComplStatus other than 0 (9 total):

| Row | Packet | Time | Channel | Type | Tag | RequesterId | CompleterId | ComplStatus |
| ---: | ---: | --- | --- | --- | ---: | --- | --- | ---: |
| 26 | 1945008 | 4.853 sec | Upstream | `0x11` | 11 | 0x0000 | 0x0100 | 1 |
| 28 | 1945013 | 4.853 sec | Upstream | `0x11` | 1 | 0x0000 | 0x0100 | 1 |
| 30 | 1945018 | 4.853 sec | Upstream | `0x11` | 7 | 0x0000 | 0x0100 | 1 |
| 32 | 1945023 | 4.853 sec | Upstream | `0x11` | 13 | 0x0000 | 0x0100 | 1 |
| 36 | 2093065 | 5.880 sec | Upstream | `0x11` | 3 | 0x0000 | 0x0100 | 1 |
| 40 | 2093075 | 5.880 sec | Upstream | `0x11` | 9 | 0x0000 | 0x0100 | 1 |
| 42 | 2093081 | 5.880 sec | Upstream | `0x11` | 15 | 0x0000 | 0x0100 | 1 |
| 44 | 2093088 | 5.880 sec | Upstream | `0x11` | 0 | 0x0000 | 0x0100 | 1 |
| 46 | 2093093 | 5.880 sec | Upstream | `0x11` | 4 | 0x0000 | 0x0100 | 1 |

Status 1 corresponds to Unsupported Request under the vendor constant
`CS_UNSUPPORTED_REQUEST = 1`. These rows were not GUI cross-checked, and no
claim is made that they are abnormal. G2b later associated all nine with
MRd(32) requests rather than configuration requests (see
[G2b evidence](pcie-g2b-evidence.md)), so a configuration-probing explanation
is not assumed here.

## Post-close integrity (13:15:40 +08:00, PETracer not running)

Source trace, working copy (ReadOnly), PETracer executable and repo/deployed
probe script retained the identities above.

## Limits

- One trace; field reads verified against the GUI on two packets only.
- `Tag`/`RequesterId` applicability per type is not established by the probe.
- No pairing, timeout, or anomaly logic was run.
