# PCIe-G1b / G1c / G1d Row Export Evidence (2026-09-14)

| Slice | Result | Claim |
| --- | --- | --- |
| G1b | **PASS** (GUI sample completed 13:00) | The v2 row export ran to natural trace end, emitted one END, and its rows re-read identically as TSV and canonical JSON. |
| G1c | **PASS** | Every TLP callback counted by G1a for 1350 (938 of 938) was exported; first and last packet indices equal G1a. |
| G1d | **PASS** | A second run on a fresh protected copy reproduced all 938 rows exactly. |

Scope for all three: TLP callbacks of the subscription `SendAllChannels`,
`SendTraceEventOnly(_PKT_TLP)`, `SendTlpType(_ANY_TYPE)` on
`S0-Remove SD7-1350.pex`. Not all PETracer events, not precise timestamps,
no transaction fields, no ground truth or diagnosis.

## Inputs

| Item | Identity |
| --- | --- |
| Source trace | `E:\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`, 105224486 bytes, UTC mtime `2026-06-11T07:12:55.2721460Z`, SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Run 1 copy (G1b/G1c) | `C:\Users\reiko\AppData\Local\Temp\pcie-g1b-20260914-9735a039\S0-Remove SD7-1350.pex`, identical identity, ReadOnly |
| Run 2 copy (G1d) | `C:\Users\reiko\AppData\Local\Temp\pcie-g1d-20260914-9230e789\S0-Remove SD7-1350.pex`, identical identity, ReadOnly |
| Analyzer | PETracer 13.26 (Build 43) BETA, SHA-256 `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| Script | `scripts/pcie/g1b-tlp-rows-1k.pevs` v2, repo and deployed SHA-256 `952996AEAAA8EB30746F19541F4819FB378B6F78491E73558645CD6E08EA8249` |
| G1a reference | `artifacts/evidence/pcie-g1a-20260914/g1a-vendor-saved-output.log.txt`, SHA-256 `C1B551461F30FD5FE863DE8BF0B95DE68F7028A6972DDCA0F1DDE99E14A17A39` |

The 10k script was not run: with 938 TLPs it would produce the same rows.

## Execution

Both runs used the same guarded GUI sequence (session helper, not repo code):
launch, file-open dialog path set and read back identical, wait for exact
title plus Ready with no dialog for 3 s, Tools -> Run verification scripts,
select the script only after its description read back
`PCIe G1b TLP row export - cap 1000 or trace end - v2`, Run, wait for the
DONE marker in the output control, Save Output with exactly this script
listed, close PETracer.

| Run | Loaded | Run requested | DONE observed | Log saved | PETracer exited |
| --- | --- | --- | --- | --- | --- |
| 1 (G1b/G1c) | 12:52:27 | 12:52:35.595 | +1.2 s | 12:52:39 | 12:52:52 |
| 2 (G1d) | 12:53:42 | 12:53:50.427 | +1.2 s | 12:53:53 | 12:54:08 |

Before run 1 succeeded, five launches on the run 1 copy stopped at helper
checks (non-ASCII title literal, a 15 s dialog wait that was too short, a
wildcard pattern error, and two transient load windows,
`Collecting Traffic Summary Report Information` and an untitled `#32770`).
In each case no script was run; the open dialog was cancelled or the loaded
trace was closed from a Ready state without saving. Integrity was checked
after all runs (below).

## Output and verification

Logs retained unmodified: `artifacts/evidence/pcie-g1b-20260914/run1-g1b-tlp-rows-1k.log.txt`
(SHA-256 `E5D5FD93A7F6F53EE933DAA0211F15B84E82035D494DEDB5D7468DCC6848F37A`) and
`run2-g1b-tlp-rows-1k.log.txt` (SHA-256 `902A9A97B3F52FAD45D6DBA2885F3B77DFB605AB8A60AD54757C6EE7BE73EE51`),
both 51891 bytes (about 55.3 bytes per row). The two logs differ only in the
vendor "Output was saved on" timestamp line.

`verify_g1b_rows.py` (with the G1a and D1 logs) returned `PASS_ROW_EXPORT` for
both runs: cap 1000, `end_reason` `trace_end`, 938 rows, `complete_export: true`,
first index 1944516 and last index 2121703 (both equal to G1a), first five rows
equal to the D1 1350 log, TSV and canonical JSON re-read equal.

`compare_g1_exports.py run1-export run2-export --expected-rows 938` returned
`PASS_REPRODUCED`: identical packet index sequence and all columns equal row by
row; rows.tsv SHA-256 `0028CC8D65948F0BCBF4149A7F50328DC815BDDB1B944F4684CE88F1EE45D3B8`,
canonical rows.json SHA-256 `A5398FB6863F63CC44D809EFF2884E3EECE53D551B1FCA18414238C5EE0C12D6`
for both runs.

Screenshots: `g1b-run1-ready.png`, `g1b-run1-result.png`, `g1d-run2-ready.png`,
`g1d-run2-result.png` in the same evidence directory.

### Descriptive composition of the 938 rows (not a diagnosis)

Display time spans `4.848 sec` to `6.055 sec`.

| Vendor channel label | Rows |
| --- | ---: |
| Downstream | 519 |
| Upstream | 419 |

| Vendor TLP type code | Rows |
| --- | ---: |
| `0x1` | 82 |
| `0x3` | 79 |
| `0x9` | 293 |
| `0xA` | 64 |
| `0xD` | 2 |
| `0xE` | 1 |
| `0x11` | 70 |
| `0x12` | 347 |

Channel labels and type codes are raw vendor values. `Upstream` rows appear in
the full export although the first five sampled rows were all `Downstream`;
no physical direction mapping or type semantics is asserted here.

## Post-close integrity (12:54:47 +08:00, PETracer not running)

Source trace, both working copies (still ReadOnly), PETracer executable and the
repo/deployed 1k script retained the size, UTC mtime and SHA-256 listed above.

## GUI sample of rows 469 and 938 (13:00, run 1 copy)

The run 1 protected copy was reopened with the same guarded load check, and
Search -> Go to Packet (Ctrl+G) was used with the index read back from the
dialog edit before OK. No script was run in this session; PETracer was closed
afterwards.

| Export row | Export values | GUI observation | Result |
| --- | --- | --- | --- |
| 1 | 1944516, 4.848 sec, Downstream, `0xE`, x1 | Earlier D1 GUI cross-check (Msg / MsgD, 4.847933004000 s, x1) | MATCHED (prior evidence) |
| 469 | 2097003, 5.897 sec, Downstream, `0x9`, x1 | Packet 2097003: TLP, Cfg / CfgRd0, direction cell `R→`, x1, time stamp 0005.896 580 076 s | MATCHED |
| 938 | 2121703, 6.055 sec, Upstream, `0x12`, x1 | Packet 2121703: TLP, Cpl / CplD, direction cell `R←`, x1, time stamp 0006.055 209 278 s | MATCHED |

Rounded GUI time equals the export display time for both rows, and link width
matches. The GUI direction cells agree with the export channel labels on these
two rows (`R→` with Downstream, `R←` with Upstream); this is an observed
correspondence on sampled rows, not a qualified physical direction mapping.
Vendor code `0x12` was displayed as Cpl / CplD for this packet; no general
code-to-type table is asserted. The GUI also shows RequesterID, Tag,
CompleterID and Status fields for these TLPs, which G2a must read and verify
separately.

Retained screenshots: `gui-row469-pkt-2097003.png`
(SHA-256 `5F4C29F2B15A89164AC9E35383DE27E52D57DE6297A202035CA9B5D78C2F4665`) and
`gui-row938-pkt-2121703.png`
(SHA-256 `B8826A578F21D82A9A3907022C5AB624E7562C6F99AD77453688303EC7457EBA`).

Post-close integrity at 13:00:41 +08:00 (PETracer not running): source trace,
run 1 copy (ReadOnly) and PETracer executable retained the identities above.
