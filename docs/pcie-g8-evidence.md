# PCIe-G8 HTML Report — Evidence (2026-09-14)

Status: **G8 PASS (prototype)**. The same 1350 findings as G7 v2 are rendered as a
layered, offline HTML page for fast scanning. Ready for a first engineer trial.

| Item | Value |
| --- | --- |
| Report | `artifacts/reports/pcie-g8-1350-20260914/report.html`, SHA-256 `2FBF90AD974CE82C4F3BA7019B59173A5F4210F027C123CC3005E6CE4FE9A18A` |
| Source | `artifacts/evidence/pcie-g3f-20260914/findings.json` (same as G7) |
| Renderer | `scripts/pcie/g8_render_html.py`; tests `tests/pcie/test_g8_html.py` |

```text
python -X utf8 -B scripts/pcie/g8_render_html.py   --findings artifacts/evidence/pcie-g3f-20260914/findings.json   --trace-file-name "S0-Remove SD7-1350.pex"   --trace-sha256 1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB   --tlp-count 938 --output artifacts/reports/pcie-g8-1350-20260914/report.html
```

## Layout (owner direction 2026-09-14)

1. Fixed notice panel at the top: ground truth `UNKNOWN`; no failure-cause judgement
   (`NOT_EVALUATED`); the 64-packet nearby range is a prototype heuristic; order is
   capture order, not severity; the navigation-anchor note.
2. Scan table, one row per finding: navigation anchor, display times, badges and a
   one-line summary. Badges: completion status (`UR`), nearby message names
   (`ERR_COR`, `SLOTPOWERLIMIT`), `同 key 再次出現`, and `N Segments，跨 X packets`.
   The span is shown as a number; no long-distance threshold is introduced.
3. Sixteen cards. First layer: 主要定位點, observation summary, segment times with
   their navigation packets. `<details>` "展開完整證據" holds the full G7 wording:
   anchors with RequesterId/Tag/Completer/status, nearby messages, GUI cross-checks,
   grouping reasons, every per-finding limitation, and traceability.

No content from G7 is dropped; limitations stay in each card so a single card read
alone keeps its boundaries.

## Consistency and safety

- Wording comes from `g7_render_markdown.finding_parts`; a test asserts that every
  observation and limitation sentence of the Markdown appears in the HTML.
- No `<script>`, no external `src`/`href` (only in-page anchors), all text HTML-escaped
  (tested with a hostile trace name). Light and dark colours via `prefers-color-scheme`.

## HTML contract (fails closed before writing)

- Cards follow `findings.json` order, all 16 present.
- Each card's first layer shows its navigation anchor; each card has expandable evidence
  containing every anchor packet, `UNKNOWN` and its finding id under traceability.
- Notice panel contains `Ground truth UNKNOWN` and the navigation-anchor note.
- Same forbidden phrases as G7 (including `建議先看`); no dash characters.

Result for 1350: 16 cards, 0 contract errors.

## Limits

- Presentation only; inherits every limit of G3c-G3f and G7.
- Not yet visually reviewed by an engineer; the first trial should report whether the
  scan table and badges let them pick cards quickly and whether the first layer is enough.
