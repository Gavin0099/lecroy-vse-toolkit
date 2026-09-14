# PCIe-G7 Markdown Report — Evidence (2026-09-14)

Status: **G7 PASS (prototype)**. The 1350 findings are rendered as a Traditional
Chinese engineering report, generated only from `findings.json` and checked by a
repository report contract before writing. G8 HTML waits for the owner's reading
of this Markdown.

| Item | Value |
| --- | --- |
| Report | `artifacts/reports/pcie-g7-1350-20260914/report.md`, 860 lines, SHA-256 `167E04988511C5BA3EED99E0A75E24A6411A7F54D9D9B1E4A7866E59814127D6` |
| Source | `artifacts/evidence/pcie-g3f-20260914/findings.json`, SHA-256 `B36283941560512B24A25C2DB6333AF9A8E4FE8FFFC76B9BAA35DCE581B02936` |
| Renderer | `scripts/pcie/g7_render_markdown.py`; tests `tests/pcie/test_g7_markdown.py` |
| Command-line metadata | trace file name, trace SHA-256 and TLP count 938 (from G1a), each labelled in the report as supplied on the command line |

```text
python -X utf8 -B scripts/pcie/g7_render_markdown.py   --findings artifacts/evidence/pcie-g3f-20260914/findings.json   --trace-file-name "S0-Remove SD7-1350.pex"   --trace-sha256 1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB   --tlp-count 938 --output artifacts/reports/pcie-g7-1350-20260914/report.md
```

## Owner decisions applied

- Main reading language is Traditional Chinese. PCIe names, packet identities and
  field names stay in English (`MRd(32)`, `CfgRd0`, `Cpl`, `UR`, `SC`, `ERR_COR`,
  `RequesterId`, `Tag`, `Packet 2093086`); a short Chinese gloss appears once in
  the glossary section.
- Engineering handover tone. Sentences say which packet did what; detector and
  lineage jargon stays in `findings.json`.
- The human-writing skill (`Enumd-private-vault/.agents/skills/human-writing`,
  MIT) is used for principles only: subject-first sentences, no reversal phrasing,
  no nominalisation, no prompt colons or dashes, stop when done. No text copied.
- `check_prose.py` is advisory. Report wording is not changed to satisfy it when
  its warnings do not fit an engineering report.

## Report structure

1. Opening paragraph: 938 TLPs, 16 locations with Go to Packet, capture order not
   severity, ground truth `UNKNOWN`, no statement about which item relates to a failure.
2. Glossary of PCIe names used in the report.
3. Overview table of the 16 findings with anchor links.
4. Per finding: 建議先看, 觀察到什麼, 相關位置 (per Segment), 為什麼列出這一項,
   目前還不能確定, 追溯 (finding, group and candidate ids in `findings.json`).
5. 資料來源 with the `findings.json` SHA-256 and the command-line metadata.

Every sentence is filled from structured `findings.json` fields with fixed
templates; the renderer performs no analysis.

## Report contract (fails closed before writing)

- Finding headings equal the `findings.json` order (capture order, no ranking); all 16 present.
- Each finding has all six sections, shows its primary Go to Packet, lists every anchor packet,
  states ground truth `UNKNOWN`, and traces back to its finding and group ids.
- No over-claims: `root cause`, `根本原因`, `confirmed failure`, `確認為故障`, `導致`, `造成了`,
  `severity`, `priority`, `嚴重度`; no dash characters.

Result for 1350: 0 contract errors.

## Advisory prose check

`check_prose.py` on the first render reported one English colon (the
`bus:device.function` format in the glossary) and twelve quoted 「附近」 phrases.
Both were reworded without changing evidence. It also showed that the first
render merged two observation sentences into one Markdown paragraph and chained
three grouping reasons with semicolons; those were fixed as well. The final run
reports 0 in every hard category and one advisory note (78% single-sentence
paragraphs), which follows from the fixed per-finding list format and is kept.

## Point for the owner's reading

The primary Go to Packet follows the fixed G3e rule (earliest request in the
group). For the long-lineage findings F003 and F009-F012 it points to the
4.848 sec CfgRd0, while the MRd(32) -> UR segment is listed under 其他位置.
The rule was not changed.

## Limits

- One trace; ground truth `UNKNOWN`; the report makes no causal or failure claims.
- Inherits G3c's prototype 64-packet heuristic (stated in each affected finding)
  and G3d's 5-row presentation window.

## Wording patch v2 (owner review 2026-09-14)

After reading the full report the owner kept the analysis and asked for three
presentation changes only. G3e/G3f rules, candidates and groups are unchanged.

1. Title `PCIe 候選問題位置報告` became `PCIe Trace 候選檢查位置報告`; the opening now
   says the tool arranged 16 groups of candidate inspection locations.
2. Section `建議先看` became `主要定位點`, with the sentence "依固定規則選出的主要定位點
   （這一組最早出現的 request）".
3. A global note states that the navigation anchor follows a fixed rule, is only for
   jumping, and does not mean the location is more severe, more suspicious or closer
   to a failure cause.

The contract now also requires that note and rejects the old `建議先看` wording.
`finding_parts` was extracted so G8 HTML reuses the same sentences.

| Version | File | SHA-256 |
| --- | --- | --- |
| v1 (reviewed) | `artifacts/reports/pcie-g7-1350-20260914/report-v1.md` | `167E04988511C5BA3EED99E0A75E24A6411A7F54D9D9B1E4A7866E59814127D6` |
| v2 (current) | `artifacts/reports/pcie-g7-1350-20260914/report.md` | `F45D70A69418BE0D1E831B9EB6D95B900CB8C5963C9C0C2ABEACCD05E64BE5CA` |

v2 contract errors: 0. Advisory `check_prose.py`: 0 in every hard category; notes
on similar sentence length and single-sentence paragraphs follow from the fixed
template and list layout and are kept.
