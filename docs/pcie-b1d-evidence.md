# PCIe-B1d 第一版實作與重播證據（2026-09-30）

結果：B1d 第一版正式產物本地 COMPLETE；來源邊界與最後兩處表格／字形修正完成。
原因：工程師回答已足以定義產品規則；初始 Gen1 僅作觀察，MUX 接通與雙向 L0 各自使用獨立證據。
下一步：後續 findings 可以使用本版各項結果；四項待補驗證條件限制對應規則，不阻擋 B1d close。

本次僅完成 B1d。本地已驗證，尚未 commit、push、建立 PR 或 merge；B1e 未實作。
此處 PASS 指本版程式／契約驗證通過，不代表此 hang case 通過，亦不代表已建立完整 PCIe 規範判定。

## 實作

- 規則契約：[pcie-b1d-rule-contract.md](pcie-b1d-rule-contract.md)。
- 工程師回答：[pcie-b1d-engineer-questions.md](pcie-b1d-engineer-questions.md)，
  2026-09-30 由使用者提供，回答人／實際回答日期未提供。
- 評估器：`scripts/pcie/b1d_mux_rules.py`，讀取 B1c-r1 v2 與顯式產品 context，
  輸出 `pcie.b1d-mux-rule-evaluation/v1` JSON 及同內容的 Markdown。
- 目前輸入 context：`artifacts/evidence/pcie-b1d-hang-20260930/product-context-r1.json`。
  以完整 SHA-256 綁定 training.json 與工程師問答；每條規則保留回答題號。
- 只接受本版已定義的 SDE insert／RC-MUX interposer／Gen3 x1 情境。
  切換起點與 reconnect packet 由 context 明確指定；本版不是自動 MUX 偵測器。

使用 PASS／FAIL／INCONCLUSIVE／NOT_EVALUATED，沒有整體 PASS／FAIL。
MUX 接通與裝置初始化完成分開儲存；缺少門檻不能變成自訂 FAIL。
只有兩方向明確、有效的 training 紀錄能成立接通判定；不取 carried state 或 invalid LTSSM 代替。
這是 Q7 的 training criterion，不依賴 L0。雙向 L0 只依兩方向明確有效的 L0 紀錄；
Q2 提供後續初始化情境。初始 speed 為 observation_only，沒有工程師接受規則的題號歸因；
context 不再包含 `initial_gen1_allowed`，評估器也拒絕這個未獲工程師定義的接受條件。
Raw speed code 的 GT/s 標示尚未 probe，本版以 GUI speed sample 作速度證據，
不將 Data Rate capability 欄位誤當目前速度。

## 真實 hang window 結果

分析輸入是既有 `artifacts/evidence/pcie-b1c-r1-hang-20260915/training.json`，
packet 225041-1484414；未重新開啟 `.pex`、VSE 或 GUI。

| 項目 | 本版結果 | 依據與限制 |
| --- | --- | --- |
| 切換 Link Down | PASS | Packet 225041，符合工程師產品情境 |
| 接通前 Recovery／Polling／無事件 | PASS（情境相符） | 單獨出現不判錯；invalid-state 標記保留，不證明完整 LTSSM 合法 |
| MUX 接通 | PASS（工程師證據規則） | 1479760 Link Up 後有雙向有效 training；非直接量測 MUX 電氣狀態 |
| 雙向 L0 | PASS | Downstream 1484273、Upstream 1484298 |
| Width 樣本 | PASS | GUI 1479761 x1、speed_width 1479845 width=1；僅限樣本 |
| 初始 Gen1 樣本 | INCONCLUSIVE（僅觀察） | 首次有效 L0 前 GUI 1479761 為 2.5 GT/s x1；工程師未確認初始 Gen1 合法，本版未驗證 spec |
| 目標 Gen3 | INCONCLUSIVE | 既有 GUI speed 樣本未見 8.0 GT/s；window 尾端不足以判定後續是否完成升速，不再使用「曾觀察到 target rate」描述缺失樣本 |
| Hot-plug 初始化活動 | INCONCLUSIVE | 雙向 L0 後輸入 window 只有兩筆 message，未見新的 config request；不推定 window 外都沒有 |
| 初始化完成 | NOT_EVALUATED | 缺少 completion criteria；不由雙向 training 或單筆 config request代替 |
| 切換事件間隔 | NOT_EVALUATED（接受度） | 9.512→10.912 的 display-time 差 1.400 sec，與工程師「約 1.4 sec」並列；不是直接量測 dead-time 或 timeout |
| Training timeout | NOT_EVALUATED | 缺適用 spec／起點／上限 |
| TS-error tolerance | NOT_EVALUATED | 共 384,993 HasErrors：2 + 382,842 + 84 + 2,065；保留時間、packet 與 sample-only subtype，沒有門檻 |

雙向 L0 到 window 尾端的 display-time 差為 0.000 sec；兩者顯示都是 10.912 sec，
不表示物理時間為零。這份輸入不足以證明後續升速與裝置初始化在哪一步失敗。
本 case 裝置不可見、system hang、BSOD 0x124 來自使用者轉述；其他測試的 0xA0
不套用到此 trace。未建立 BSOD 根因。

## 輸出與重播

- [目前正式 Markdown 評估](../artifacts/evidence/pcie-b1d-hang-20260930/r2-run1/evaluation.md)
- [目前正式 JSON 評估](../artifacts/evidence/pcie-b1d-hang-20260930/r2-run1/evaluation.json)
- [最後兩處文字修正與完整 hash 證據](../artifacts/evidence/pcie-b1d-hang-20260930/verification-r2.json)
- [r1 規則修正與兩次重播證據](../artifacts/evidence/pcie-b1d-hang-20260930/verification-r1.json)
- [目前 PCIe 測試紀錄](../artifacts/evidence/pcie-b1d-hang-20260930/r1-pcie-tests.log)

```powershell
python -X utf8 -B scripts/pcie/b1d_mux_rules.py `
  --training artifacts/evidence/pcie-b1c-r1-hang-20260915/training.json `
  --context artifacts/evidence/pcie-b1d-hang-20260930/product-context-r1.json `
  --source-document docs/pcie-b1d-engineer-questions.md `
  --output-dir artifacts/evidence/pcie-b1d-hang-20260930/r2-run1
```

上列是目前正式報告的實際命令；`r2-run1` 已存在，再執行會拒絕覆寫。
r2 的 evaluation.json 與 r1 位元組完全一致；Markdown 精確只有兩处變更：
BIDIRECTIONAL_L0 的表格來源改為「trace observation；Q2 提供後續初始化情境」，
以及「双向」改為「雙向」。判定與觀察資料不變，輸入 hash 保持相同。
r1 的兩輪重播 JSON／Markdown 完全一致證據仍保留；r2 僅修 rendering 文字，未重跑整套測試。

- evaluation.json SHA-256：`22ED4A80E2917FE547693D6BD43AF82CD496C34FFAA5B882DA699622C3EC240A`
- evaluation.md SHA-256：`698EF7B82B7918306D62A22AA096BD9E67235FD91994CCCBDCAFDD7F4C015802`

原 `product-context.json`、`run1/`、`run2/` 與 `verification.json` 留作歷史，
其初始 Gen1 PASS 與舊文字已由本次 r1 修正取代，不能當作目前接受規則。
r1 的規則與測試證據仍適用；目前報告以 r2-run1 為準。

## 驗證

- r1 規則修正驗證：`python -X utf8 -B -m unittest discover -s tests/pcie -p test_b1d_mux_rules.py -v`，21 個測試通過。
- r1 回歸驗證：`python -X utf8 -B -m unittest discover -s tests/pcie -v`，138 個測試通過。
- r2 報告修正驗證：evaluation.json 位元組不變，Markdown 僅指定兩處文字改變，輸入 hash 不變。
- 新增回歸：初始 Gen1 只能是 observation_only／INCONCLUSIVE；target speed 正／負樣本
  文字一致；雙向 training 而沒有 L0 可得到 MUX_CONNECTIVITY=PASS、BIDIRECTIONAL_L0=INCONCLUSIVE；
  只有 L0 不能代替 Q7 的 training criterion。
- 負向／邊界涵蓋單向 training、invalid／carried state、缺一側 L0、非 x1、缺 width、
  未 probe speed code、GUI capability 與當前 speed 區分、L0 前／錯方向 config、
  config request 不證明完成、未定 time／error 門檻、壞 phase／gap／count、
  hash 不符及拒絕覆寫。Expected status 來自本版契約與工程師回答。
- 真實案例核對獨立 B1c-x2 的 384,993 計數與 B1c-r1 的兩個 L0 packet。
- B1c 程式、歷史 training.json／training.md 與其 PASS 結果維持原有範圍。
- `git diff --check`：PASS。

四項待補條件為 training timeout、TS-error tolerance、Gen3 convergence、hot-plug completion。
它們保留在 JSON 的 `validation_debt`，均為 `blocks_this_version=false`。
回答人／實際回答日期、0x940h[1] 的 register 定義可另補來源；本版不執行 register 操作。
跨 case 正確性、完整規範驗證、電氣量測、root cause 及 B1e/B2/B3 均未建立。
