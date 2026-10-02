# PCIe-B1e：Link findings 驗收

2026-09-30 本地完成；沒有 commit、push、PR 或 merge。

## 結果

B1d 的 12 項狀態、packet 證據與限制均保留。此 hang window 沒有可成立的
RULE_MISMATCH，不表示整體產品正常。MUX 接通、雙向 L0 及 x1 樣本已有支持；
Gen3 樣本與 L0 後 config 活動仍為 INCONCLUSIVE，調查焦點在 L0 後。
Initial Gen1 只作觀察，四項 validation debt 仍不阻擋本版。

Window 有一筆 NAK（225042），不推成 replay；CRC flags 為 0 只限既有
window 計數。Recovery state 紀錄不當作完整 Recovery entry 次數。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b1e_link_findings.py -v`：7 tests PASS。
- 真實 B1d r2 evaluation、B1c-r1 training、工程師問答各以相同內容重播兩次。
- `artifacts/evidence/pcie-b1e-hang-20260930/verification.json`：JSON／Markdown
  位元組一致，來源 hash 與 evaluation 所引用的 training／問答一致。
- 測試包括 width FAIL fixture、training/L0 獨立、缺 CRC 不補 0、竄改來源／狀態
  拒絕、hash 不符及已有輸出目錄拒絕。

目前正式產物是 `artifacts/evidence/pcie-b1e-hang-20260930/run1/findings.json`
與 `findings.md`；`run2` 為重播證據。

## 限制

沒有擴張 B1d 規則、推導 root cause 或對整體 case 宣告 PASS。
工程師轉述的 device 不可見與 BSOD 是故障現象，不反推 MUX 失敗。
下一個獨立 gate 為 B2a：先 probe register 欄位，才建立 config log。
