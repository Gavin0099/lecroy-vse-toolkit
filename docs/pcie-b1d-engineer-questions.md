# PCIe-B1d：MUX 切換規則確認清單（給工程師）

Trace：`Disable ASPM--Insert SD7-hang.pex`（分析對象為 13.26 轉換後副本，SHA-256 `C6E9646B...`）
整理日期：2026-09-15
依據：B1c-r1 training timeline（commit `c100ee1`）、B1c-x1/x3 GUI 抽樣（commit `23fe07c`）

回覆收錄日期：2026-09-30（Asia/Taipei）。以下回答由使用者於本次對話提供；回答人姓名與實際回答日期未提供。收錄日期不代表工程師回答日期。
回覆屬於工程師提供的產品預期與故障描述；本次未重新開啟 trace 或驗證 PCIe spec。

## 為什麼要問

工具目前只整理 trace 裡看到的事實，還沒有判斷任何地方合不合理。下一步（B1d）要把
「SD/SDE 插拔時 MUX 會切換 PCIe path，舊 link 斷掉、新 link 重新 training」這個產品
行為變成明確規則。規則必須由工程師提供，工具不自行假設。

**B1d 第一版最少需要第 1 到 4 題。** 其餘可以之後補。

每題的「這份 trace 看到的」只是事實，不代表工具已經認為正常或有問題。packet 編號
來自轉換後的 13.26 trace。

---

## 1. MUX 切換時，哪一側的 Link Down 是預期的？（必要）

這份 trace 看到的：

- 9.512 sec，Packet 225041：Upstream `Link Down`（GUI 已核對）。
- 9.538 至 9.575 sec：Downstream 出現 `LINK_DOWN` / `LINK_UP` 交替共 12 筆。
- 10.912 sec，Packet 1479760：Upstream `Link Up`（GUI 已核對）。

請確認：

- 預期是 Downstream、Upstream，還是兩側都可能出現 Link Down？
- analyzer（interposer）接在 MUX 的哪一側？這份 trace 看到的是切換前的 path、切換後的 path，還是兩者都有？

回答（依使用者提供的工程師回覆整理）：

1. Link 兩端都會出現 Link Down。
2. Interposer 接在 MUX 與 RC 之間。
3. 插入卡片後，SW 確定接上的是 SDE 卡，會寫入 `0x940h[1]` 進行 MUX switch；先斷開 RC to controller，約 1.4 sec 後接上 RC to SDE card。
4. 工程師解讀：9.512 sec 是 7494 controller 與 RC 斷開；RC 進入 Recovery，開始發 TS1，接著進入 Detect（9.538 sec），過一段時間後 Link Down（9.562 sec）。
5. MUX switch 約 1.4 sec，所以約 10.911 sec 會看到 EP 這一端 Link Up，此時已切換到 SDE card。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

待核對：`0x940h[1]` 的所屬裝置、register 定義與寫入值尚未提供；本次只保留工程師原述。工程師對 9.538 sec Detect 的解讀，與上方 analyzer timeline 的標示需再對照；10.911 sec 與已記錄的 10.912 sec 也保留各自來源，不直接改寫原始觀察。

## 2. 正常的重新 training 流程應該長什麼樣？（必要）

這份 trace 看到的（依時間）：

- Downstream：Recovery.RcvrLock → Recovery.Speed（伴隨 Link Down/Up）→ Recovery.RcvrLock → Polling（analyzer 標示 state not valid），到 9.600 sec。
- 9.600 至 10.912 sec：沒有觀察到任何事件（約 1.312 sec）。
- 10.912 sec：Upstream Link Up → Polling → 雙向 Configuration（LinkWidth → Lanenum → Complete）→ 雙向 Recovery.RcvrLock / RcvrCfg → 雙向 L0。
- Detect 只在 9.512 sec 的 Upstream 出現一次（analyzer 標示 state not valid）。

請確認：

- 預期流程是否為 `Link Down → Detect → Polling → Configuration → L0`？
- 中間允許進入 Recovery 嗎？允許幾次？
- Link Up 之前先看到 Recovery 或 Speed change，是否預期？

回答（依使用者提供的工程師回覆整理）：

1. 預期在約 10.911 sec 後，看到 RC 對 EP 做初始化，例如讀取 config space、寫入 BAR，一直到後續對 SDE card 的 emulation。
2. Training 中可以進入 Recovery，依照 PCIe spec 即可。
3. MUX 斷開 RC to controller、尚未接回之前，RC 因 link 突然消失而產生 Recovery 或 Polling，工程師認為是正常行為。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

待確認：PCIe spec 版本、適用章節與狀態／時限條件尚未提供；沒有提供 Recovery 次數上限，也尚未把問題中的簡化狀態序列確認為唯一合法流程。

## 3. 重新 training 最慢可以花多久？（必要）

這份 trace 看到的：

- 第一次 Link Down（9.512 sec）到雙向 L0（10.912 sec）約 1.40 sec。
- 其中 9.600 至 10.912 sec 約 1.312 sec 完全沒有觀察到事件（時間解析度為 PETracer 顯示值 1 ms）。
- Downstream 在 9.512 至 9.600 sec 約 88 ms 內送出大量 TS1。

請確認：

- 從 Link Down 到回 L0 的允許上限是多少？
- 約 1.3 sec 沒有任何 link 活動，在 MUX 切換期間是否可能？

回答（依使用者提供的工程師回覆整理）：

1. Training 時限依照 spec 規定。
2. MUX 切換期間 link 是斷開的；interposer 可能看到 RC 向 Downstream 做 Recovery 或 Polling，也可能沒有任何活動。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

待確認：尚無可執行的 training timeout 數值與 spec 依據。約 1.4 sec 是工程師描述的 MUX 切換時間，不直接當作 PCIe training 的允許上限；需要區分 MUX 斷開時間與重新接通後的 training 時間。

## 4. 重新連線後，預期的 Speed / Width 是多少？（必要）

這份 trace 看到的：

- 切換前 Downstream TS1（Packet 225052 起）：5.0 GT/s x1，Data Rate 欄位列出 2.5 至 16.0 GT/s。
- 9.552 sec 起 Downstream 為 2.5 GT/s x1。
- 空白後 Upstream TS1（Packet 1479845 起）：2.5 GT/s x1，Data Rate 列出 2.5 至 8.0 GT/s。
- trace 在 10.912 sec 回到 L0 後不久就結束，之後是否再做 speed change 無法觀察。

請確認：

- 重新連線後必須回到哪個 speed（例如 Gen3、Gen4）？停在 2.5 GT/s x1 可以接受嗎？
- width 預期是 x1 嗎？

回答（依使用者提供的工程師回覆整理）：

1. SDE 卡應該是 Gen3，7494 controller 是 Gen2；停留在 Gen1 就有問題。
2. Width 是 x1，只會有 x1。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

判定限制：這份 trace 在 10.912 sec 回到 L0 後不久結束，尚無足夠後續觀察證明是否持續停留在 Gen1。仍需確認完成升速的觀察終點或時限；不能只因最初以 Gen1 training 就判定失敗。

來源界線（2026-09-30 修訂）：工程師回答沒有確認初始 Gen1 是可接受行為；本版也未重新驗證 PCIe spec。首次有效 L0 前的 2.5 GT/s x1 樣本只記為觀察證據，INITIAL_GEN1_SAMPLE 為 INCONCLUSIVE，不歸為工程師接受規則。

---

## 5. MUX 切換期間出現 Training Sequence Error 是否可能是預期的？

這份 trace 看到的：

- 384,993 個 Downstream TS1 被 PETracer 標為 `HasErrors`：Recovery 期間 2 個、空白前 Polling 382,842 個、空白後 2,149 個。
- GUI 抽樣 3 筆（只代表這 3 筆）：
  - Packet 1096918 與 1479761：`TSRsrvErr`（RSVD `0, 1, 0`，Data Rate 帶 Reserved bit，Link/Lane 為 PAD）。
  - Packet 990799：`TSDataRateErr`、`TSRsrvErr`、`TSLaneErr`、`TSTrainingControlErr`。
- 空白後 Upstream 的 TS1 沒有被標 `HasErrors`。

請確認：切換瞬間出現這類 TS 錯誤是否可以接受？如果可以，數量或持續時間有沒有上限？

回答（依使用者提供的工程師回覆整理）：

1. MUX 切換期間出現這類錯誤，工程師認為應該是正常現象。
2. 數量及持續時間都不可太多；預期在幾個 TS1 之後就應該認到正常的 TS1。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

待確認：「幾個 TS1」的筆數、持續時間、計算起點與適用階段尚未量化。這份 trace 的 384,993 筆 HasErrors 不能因此全部判為可接受，也不能在沒有門檻時全部判為異常；GUI 的錯誤細節仍只代表已抽樣的 3 筆。

## 6. Link 回到 L0 之後，RC 預期接著做什麼？

這份 trace 看到的：

- 9.512 sec，Link Down 同時段：RC 對 `001:00.0` 送出 `CfgRd0`（Register 0x200，Tag 6）兩次，都沒有觀察到 Completion。
- 10.912 sec 回到 L0 後，trace 裡只剩 `VENDOR1` message（Upstream）與 `SLOTPOWERLIMIT` message（Downstream），接著 trace 結束；沒有觀察到新的 config 存取。

請確認：回到 L0 後 RC 預期會重新 enumerate、重讀 config space、重設 BAR、重新設定 ASPM，還是直接恢復原本的 transaction？

回答（依使用者提供的工程師回覆整理）：

原本 RC to controller 已經切斷，接上 SDE card 後，預期是 hot plug 上新的 device，所以應該重新初始化。依第 2 題回答，預期包括重新讀取 config space、寫入 BAR，以及後續對 SDE card 的 emulation。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

判定限制：本 trace 的尾端未觀察到新的 config 存取，但 capture 很快結束，尚不能證明 RC 在完整後續流程中都沒有進行初始化。ASPM 的具體重設步驟及 register 判定條件也尚未提供。

## 7. 什麼情況你會認定 MUX 切換沒有完成？

請勾選或補充，並盡量給數值：

- [ ] 沒有回到 L0
- [ ] Recovery 超過 ___ 次
- [ ] speed / width 不符合第 4 題
- [ ] training 超過 ___ sec
- [ ] Link Up 之後 ___ sec 內又 Link Down
- [ ] EP config space 沒有恢復（哪些 register：___）
- [ ] 其他：___

回答（依使用者提供的工程師回覆整理）：

MUX 切換如果沒有完成，只會看到 RC 向下發的 packet，不會看到 Upstream packet。工程師認為這個 case 的 MUX 切換已完成，因為已看到 link 兩端開始進行 training。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

判定限制：上述是工程師對 MUX 接通的判斷，並未把勾選項目或數值門檻補齊。雙向 training 不代表 hot-plug 初始化、enumeration 或裝置可見性已成功，也不證明 hang 的原因。

## 8. 這個 case 實際的故障現象是什麼？

例如 BSOD（stop code：___）、裝置消失、driver timeout、系統卡住、重新 enumeration 失敗。
也請確認測試條件：檔名中的「Disable ASPM」與「Insert SD7」是否代表 ASPM 關閉、插入 SD7 卡時發生？
回覆收錄前，這份 trace 的 ground truth 記為 `UNKNOWN`。本次已取得下方由使用者轉述的故障描述；既有 extraction／training JSON 的 `UNKNOWN` 保留為歷史資料，本次未改寫。

回答（依使用者提供的工程師回覆整理）：

1. 主要問題是切換後看不到 device。
2. 這份 trace 的測試條件確實是關閉 ASPM、插入 SD7 後 system hang，並出現 BSOD `0x124`。
3. 其他測試可能出現 BSOD `0x124` 或 `0xA0`；未提供這些測試對應的 trace 或記錄。

回答人／日期：未提供；由使用者於 2026-09-30 轉述。

證據範圍：本 case 的故障描述現在有使用者轉述來源；尚未提供測試記錄或 crash dump。`0xA0` 屬於其他測試，不能直接套用到這份 trace；本文件不推定 BSOD 根因。

---

## 回覆收錄後的 B1d 規則整理

以下整理本版規則的產品輸入。2026-09-30 使用者確認，現有回答已足夠建立 B1d
第一版；未量化條件是待補驗證項目，不是開工 blocker。第一版規則契約見
[pcie-b1d-rule-contract.md](pcie-b1d-rule-contract.md)；實作與重播證據見
[pcie-b1d-evidence.md](pcie-b1d-evidence.md)。

| 項目 | 工程師提供的預期／描述 | 可判定範圍與待補條件 |
| --- | --- | --- |
| MUX 拓撲與動作 | Interposer 在 RC 與 MUX 之間；由 7494 controller 切到 SDE card，先斷開再接通，約 1.4 sec | 可記為產品情境；register 定義與寫入值、時間／state 對照仍待確認 |
| 切換期間 Link Down／Recovery／Polling／無活動 | Link 兩端會 Link Down；接回前的 Recovery、Polling 或無活動可以出現 | 單獨出現這些現象不足以判定故障；合法狀態條件與時限仍待 spec 依據 |
| Training 時限 | 依 PCIe spec | 待版本、章節、起算事件與數值；約 1.4 sec 不作 timeout |
| 連線 speed／width | SDE Gen3 x1；7494 controller Gen2 x1；持續停在 Gen1 有問題 | 待完成升速的觀察終點／時限；目前 trace 尾端不足以判定持續停留 |
| TS 錯誤 | 切換期間可能發生，應在幾個 TS1 後恢復正常 | 待錯誤筆數、時間、起點與適用階段；不能直接接受全部 384,993 筆 |
| MUX 接通與裝置初始化 | Q7 的雙向 training 支持工程師判斷 MUX 已切換；新 SDE 裝置應重新初始化 | MUX 接通不要求雙向 L0；雙向有效 L0、enumeration 與裝置可見性各自有證據 |
| 本 case 故障描述 | 關閉 ASPM、插入 SD7 後裝置不可見，system hang、BSOD 0x124 | 使用者轉述的工程師描述；根因未建立，0xA0 僅屬其他測試 |

已有回答可建立產品規則與觀察型判定。Training timeout、TS-error tolerance、
Gen3 convergence deadline／endpoint、hot-plug 初始化完成條件保留為 validation debt；
對應規則以 NOT_EVALUATED 或 INCONCLUSIVE 表達，不自行填入門檻。回答人／實際回答
日期與 register 定義仍可後補；產品預期的來源目前明確記為使用者轉述。
本版完成範圍依 B1d evidence 定義，不提升為完整數值驗證或根因診斷。
