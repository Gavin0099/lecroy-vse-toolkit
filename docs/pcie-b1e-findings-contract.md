# PCIe-B1e link findings 契約

2026-09-30 使用者授權逐段往下做；能在現有範圍排除的問題不中斷。
B1e 使用已收下的 B1d 第一版，不增加接受門檻、不重新調查 MUX 接通。

## 輸入與輸出

輸入是 B1d evaluation.json、相同 B1c-r1 training.json 與工程師問答文件。
先檢查輸入 hash，再用 B1d evaluator 檢查 evaluation 與當前規則一致，
拒絕遭更改的 status、來源或 evidence。輸出 `pcie.b1e-link-findings/v1` 與 Markdown。
每個 finding 保留穩定 ID、rule_id、原 status、來源 pointer、packet 證據及原限制。

| 類別 | 使用條件與意思 |
| --- | --- |
| EXPECTED_CONTEXT | 切換 Link Down／斷開期間情境相符，不作異常 finding |
| SUPPORTED_MILESTONE | 已取得 MUX training、雙向 L0 等明確觀察；仍限原規則範圍 |
| RULE_MISMATCH | 原 B1d 為 FAIL，僅表示明確期待與觀察不符；目前只有 width mismatch 可成立 |
| EVIDENCE_GAP | 原 B1d 為 INCONCLUSIVE，缺觀察不能改為 FAIL |
| UNEVALUATED_RULE | 原 B1d 為 NOT_EVALUATED，缺接受門檻不能改為 PASS |
| OBSERVATION_ONLY | INITIAL_GEN1_SAMPLE 等純觀察，不補工程師或 spec 接受規則 |

另保留 window 內的 NAK 紀錄、Recovery state 紀錄、raw speed/width 紀錄和 CRC flag 計數。
NAK 不叫 replay；Recovery 紀錄不當作完整 Recovery entry 次數；缺失 CRC 旗標是 UNKNOWN，
不是 0。CRC/TS flag 只是 analyzer 觀察，不在沒有規則時生成產品 FAIL。

## 調查焦點

MUX_CONNECTIVITY 與 BIDIRECTIONAL_L0 都有支持時，指向 L0 後的 Gen3 收斂與新裝置初始化。
兩個 milestone 保持獨立。只有 training、不足 L0 時先補 L0 證據，不反推 MUX 失敗。
沒有足夠接通證據時才保留接通證據缺口；不是對已收下 B1d 的重開。
Device 不可見／BSOD 僅引用使用者轉述的 case symptom，不轉成前段根因。

本版不給整體產品 PASS/FAIL、不建立根因、不自訂 timeout/error 門檻。
四項 B1d validation debt 原樣傳遞，`blocks_this_version=false`。

## 驗收

- 正向 fixture 保留 B1d status 與 evidence，focus 指向 L0 後。
- Width mismatch fixture 可成為 RULE_MISMATCH，expected context 不可被誤當 anomaly。
- NAK/CRC/Recovery fixture 只產生觀察；missing CRC 保持 UNKNOWN。
- Training PASS/L0 INCONCLUSIVE 的獨立狀態保留。
- 改過 status/evidence/source 的 evaluation、錯 input hash、已有輸出目錄都拒絕。
- 真實 hang 輸入重播兩次，輸出位元組一致，輸入 hash 不變，原 B1d/B1c 保持原有範圍。
