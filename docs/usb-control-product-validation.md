# TRIAGE-1 產品驗收準備（2026-10-16）

目前狀態為 **Prototype PASS / Product Validation Pending**。保留先前開發資料驗證
的成果與限制；本輪不新增或調整分析規則，也沒有新的盲測或工程師省時結果。

## 可直接審查的完整報告

本輪補齊 A/B 入口連結的全部 18 份詳細 HTML 與對應 inspection.json，另附桌面、
展開證據與窄版截圖。HTML/CSS/JavaScript 均在本機，無需安裝或連線；先完整解壓縮
再開啟 `START-HERE.html`。ZIP 不包含原始 .usb、完整 raw exports 或 82MB JSON。

本機成果目錄：
`C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-validation/`

審查重點為 `portable-review/Vse/fail_01/report.html`、`fail_06/report.html` 與
`pass_04/report.html`。這三頁是既有輸出的逐位元複本，沒有為審查重寫內容。

## 原型凍結

`freeze/manifest.json` 記錄 11 個來源／測試／合約檔案的 SHA-256，另保存實際檔案、
既有 A/B 評估及三份輸出模型作為格式樣本。規則為 `usb2-control-guidance-3`，輸出
`usb-control-inspection/v1`，預設後端 Vse；閾值與設定在來源內，沒有外部設定檔。
此為本機快照，並非 Git 提交或發行版本。後續盲測須先比對 manifest；若改規則，
另外命名版本，該批資料即轉為開發／回歸資料，不回填為原版盲測通過。

## 畫面審查

使用 ux-heuristics 技能做有限範圍的啟發式審查，**6/10**。這是下表四項未滿足
診斷各扣一分的工作評分，不是使用者測試分數或工程師省時證據。最高嚴重度為 2
（可能造成停頓或額外確認），尚未觀察到真人任務失敗。

| 診斷 | 結果與依據 |
| --- | --- |
| 立即知道目前是哪份頁面 | 未滿足：頁首只有通用標題；trace hash 在底部收合區 |
| 主要動作明確 | 滿足：先看主要候選，位置、現象、理由、下一步同一張卡 |
| 導航清楚 | 未滿足：詳細頁沒有回索引／A-B 路徑提示；需依賴瀏覽器返回 |
| 能找到搜尋 | 不適用：此頁最多三張卡；瀏覽器文字搜尋可用，沒有完整 trace viewer |
| 狀態與覆蓋清楚 | 未滿足：FAIL_06 主畫面只說另外兩個，省略一個需展開底部限制才知道 |
| 錯誤／空狀態有用 | 滿足：PASS_04 明說無候選不代表 USB PASS，指出分析範圍限制 |
| 可以返回或取消 | 滿足：原生 details 可收合，瀏覽器返回保留正常行為 |
| 不靠 hover | 滿足：證據與候選有可見 summary，沒有 hover 才顯示的核心資訊 |
| 互動有標籤 | 滿足：複製時間、複製 Transfer 編號與展開項目有文字 |
| 不必猜下一個操作 | 未滿足：有編號但缺 LeCroy 定位步驟，對話框預設 Packet，需選 Transfer |

| 需修正的介面問題 | 嚴重度 | 下一版具體修正 |
| --- | ---: | --- |
| 單開詳細頁不易確認 trace 身分 | 2 | 頁首顯示中性檔案識別、短 hash、後端及規則版本；識別資訊不進排序 |
| 離開索引後缺乏導航 | 2 | 加入回索引／目前後端與檔案路徑；單檔版提供明確來源資訊 |
| 省略候選資訊埋在限制中 | 2 | 主畫面顯示「找到 4 段，顯示前三，另 1 段未顯示」並提供完整列表入口 |
| 回到 LeCroy 的步驟不在報告中 | 2 | 提供下面已核對的定位說明，明示 Transfer 與 Packet 不同；一鍵跳轉另外驗收 |

完成上述四項後，才可依同一診斷重評至 10/10；仍不能由啟發式分數宣稱產品驗收
通過。本輪只記錄問題，保留凍結 HTML 與程式。未做完整鍵盤／螢幕閱讀器、對比度
或跨瀏覽器無障礙驗收。窄版沒有橫向溢出也不代表完整行動裝置驗收。

## LeCroy 實際落點

本機 LeCroy 10.40 Build 6309，開啟來源的唯讀副本。從凍結模型讀取候選編號後
呼叫 `GotoUnit(3, transfer)`，再以 Windows Computer Use 直接檢視畫面。
下列四個落點的 Transfer 編號、時間、Address 與 EP 均實際可見，截圖保存在
`native/*.png`；這比先前只記錄 API 返回多了一層畫面證據。

| Trace | Transfer | 畫面時間（秒） | Address/EP | 畫面請求 |
| --- | ---: | --- | --- | --- |
| FAIL_01 | 1386 | 35.611541400 | 13/0 | Configuration descriptor index 0 |
| FAIL_06 | 562 | 40.351786032 | 19/0 | Configuration descriptor index 0 |
| FAIL_06 | 372 | 27.608155682 | 5/0 | BOS descriptor |
| FAIL_06 | 446 | 33.191925582 | 12/0 | BOS descriptor |

FAIL_01 與 FAIL_06 的 562 在初始 Packet 畫面可見 SETUP、DATA0、ACK 及接續 IN/NAK。
僅觀察該起始畫面，沒有逐一驗證整段傳輸終止、所有 child packet 或根因。
372／446 的 GUI Cplt 欄為空白，不把它當作狀態完成證明，也不把它與 VSE Completed
欄位直接視為相同語意。Packet 畫面的時間／欄位與 VSE duration 也未新增等價主張。

另透過原生 UI 從 FAIL_06 Transfer 446 返回 372，操作為：

1. 確認開啟與報告相同的 trace。
2. Search → Go to Packet/Transaction/Transfer（選單顯示 Ctrl+G）。
3. `Go to` 選 **Transfer**，不是預設的 Packet。
4. 輸入報告編號並按 OK；核對時間、Address、EP 與請求種類。
5. 若看到 Packet 層，可用工具列 View Transfer Level（tooltip 顯示 Ctrl+4）。

實際 UI 測試以 `set_value` 設定編號；較早的 `type_text` 沒改變可見欄位，未送出
該值。沒有驗證「HTML 複製 → 作業系統剪貼簿 → 原生貼上」整條鏈，也沒有把
驗證用 COM helper 算成產品的一鍵跳轉功能。真人操作成本仍待觀察。

## 下一個人工驗收

先由未看過案例的工程師閱讀上述報告，確認能說出主要候選、觀察事實、證據缺口，
並在 LeCroy 核對位置。本批只用於 UI 熟悉與回歸，不能重新命名為陌生 trace 盲測。
尚無新增案例及工程師實測，因此以下項目保留待驗：

- 未參與開發的 FAIL/PASS：事前封存 trace hash 與規則快照，答案由另一人保管；
  分析完才揭露答案，記錄前三是否命中、有用但未標註的候選與漏失。
- 比較傳統流程與工具流程：優先使用不同但可比較的案例，或讓不同工程師／不同
  順序交錯；同人重看同檔會學到答案，需標示練習效應，不能當獨立省時證明。
- 工具總時間含載入、分析、閱讀、定位、核對；同時記錄結果是否正確、錯誤方向數、
  未完成與求助次數。錯誤或未完成不能計入成功省時案例。

`portable-review/acceptance-record.csv` 是空白紀錄表，沒有填入示例數字。可用的省時
比例為 `(人工總時間 - 工具總時間) / 人工總時間`，只對結果正確且流程完成的可比較
紀錄計算；樣本數、學習效應與取得資料時間仍須一起保留。沒有新增自動排程或聯絡工程師。

## 驗證與交付邊界

封存與 ZIP 檢查記錄在 `package-verification.json`，來源完整性與凍結比對記錄在
`final-verification.json`。本輪的變更為驗收文件、PLAN／closeout 追加與本機報告包；
沒有提交、push、PR、merge、硬體操作或原始 trace 存檔。分析程式未變更，先前
45 項測試結果仍保留其原驗證範圍，本輪不以重跑相同單元測試代替產品驗收。
