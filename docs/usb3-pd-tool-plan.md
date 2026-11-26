# USB Trace Triage Tool：USB3／PD 擴充計畫與切片

日期：2026-10-19，r1。依據 [資料／定位實測](usb3-pd-feasibility-20261019.md)。
使用者已於可行性驗證後授權依序實作；以下表格是各片的範圍與驗收要求，
實際進度以 `PLAN.md` 最新實作紀錄及後續結果文件為準，不以計畫表當成完成證據。
本輪可做的本機工程已完成，逐片證據與外部待驗證見 [實作結果](usb3-pd-tool-results.md)。
現有 USB2 EP0 結果、未完成人工驗收與 10.50 限制維持原範圍。

## 交付目標

工程師仍只匯入一份 `.usb`。工具辨識本次可見的協定，針對已支援的分析範圍列出
少數值得調查的區段；每個候選提供位置、觀察、推薦理由與下一步，並能回到同一份
唯讀副本的正確 Packet／Transfer。沒有 PASS trace 或失敗時間也能開始。

第一版 USB3 聚焦 Link Command／LFPS 的重複流程與前後文，使用已取得的欄位。
第一版 PD 聚焦基本電力協商，以及 Discover／Enter Mode／DP Configure 的 VDM 證據。
VDM 納入是因目前 Billboard 工作情境與原生欄位均適合先驗證；不據此推論 Billboard 根因。

沿用目前原生 WinForms 布局、配色、Python controller、PowerShell acquisition、
STA COM worker、來源保護及報告形式，不另做桌面框架或完整 protocol viewer。
Triage 需新增有界分析邏輯；既有 C5 配對排名只能保留為可選比較功能，不能冒充單檔排序。

## 資料策略與最小整合

| 部分 | 沿用 | 最小新增 |
| --- | --- | --- |
| USB2 | 已凍結的擷取、候選、engine、原生 UI | 只做相容的介面銜接，保留既有候選及定位回歸 |
| USB3 | U02／U03 欄位、M2 event timeline 與既有 decoder 名稱 | 串流／有界輸出 adapter、候選聚合、Packet 定位 |
| PD | Automation Transaction／Transfer grouping、已有 VDM／PDO／RDO 顯示資料 | 耐變動欄位的 adapter；只有 Packet/header/缺欄需最小 VSE |
| 原生導航 | PID／啟動時間／caption 綁定、候選白名單、mutex、STA pump、同檔重用 | 候選綁定增加 protocol、level、index 與輔助核對資訊 |
| 工程師工作區 | 候選列表、詳情／前後證據／限制分頁、複製位置 | 各協定的欄位顯示與分析範圍狀態，不用 Address／EP 硬套 PD |

共用的只有工作生命週期、展示及定位目標。事件與判斷語意留在各自 adapter／analyzer，
不先建立 USB2／USB3／PD／PCIe 共用事件框架。

定位目標最少包含來源 hash／綁定副本、protocol、native level、index；時間與 channel
用於核對，PD 可附 SOP／訊息類型，USB2 保留 Address／EP。
索引 8 的 PD Transfer 與索引 8 的 USB3 Packet 不能只靠數字識別。
具體欄名在第一片實作時收斂，保留現有 USB2 報告相容性。

每個 analyzer 分別回報「已分析／未觀察到該協定／資料部分缺漏／尚未支援／執行失敗」。
檔名、CC 計數與單一 Packet 速度不能代替協定盤點。
沒有候選、沒有 PD、擷取被截斷，均不能顯示整份 USB PASS。

多協定結果先按協定分組，各組最多三個候選並保留完整數量；預設打開有候選的組別，
多組同時有候選時顯示清楚的組別入口，不以未校準的分數混排或隱藏其他組別。
同一來源時間接近可作「附近事件」，未核實共同時基／因果條件前不寫成跨協定根因。

## 切片與驗收

| 順序／Slice | 可交付行為 | 必須通過的驗收 | 估計人日 |
| --- | --- | --- | ---: |
| 1. EXP-01 協定範圍與分層定位 | controller／原生 UI 保留 USB2，相容接收 Packet 或 Transfer 目標；顯示各協定可見及分析狀態 | 原 USB2 四個定位點不變；USB3 Packet 8／629253、PD Packet 160／Transfer 6／8 到正確副本、編號及時間；連續／重複定位只開檔一次；拒絕錯層級、錯 hash、過期候選 | 2～3 |
| 2. U3-01 沿用擷取資料 | U02／U03／M2 輸出供單檔 analyzer 使用，保留來源、raw、vendor 名稱與 cap／缺漏狀態 | 兩份使用者 USB3 及 LinkUp 範例重跑；sample 與全程計數不能混淆；時間用整數奈秒，未知欄位不補 0；正常 USB2-only 檔明確顯示未觀察到 USB3 | 1～2 |
| 3. U3-02 單檔候選與提示 | 對 Link／LFPS 附近的重複嘗試、Reset／Wake 後續可見行為聚合成區段；提供首次位置與後續發展 | 不使用 FAIL 檔名／已知時間／PASS baseline；正常 Wake 不單獨觸發；短擷取、恢復成功、同一段多次重試、不同 channel 分開處理；每個判斷有可核對證據及具體提示 | 3～5 |
| 4. U3-03 原生工作區串接 | USB3 主要候選／前後事件／Packet 定位走完整流程 | 單候選、多候選、無候選、部分資料四種畫面；匯入→分析→核對 Packet／時間／channel；USB2 回歸及副本保護；留存操作與耗時紀錄 | 2～3 |
| 5. PD-01 Automation 資料 adapter | 先讀原生 Transaction／Transfer；最小 VSE 補 Packet/header 證據，不重建現成分組 | 五份官方範例的 9／10／8／3／15 Transfer 與 native 輸出一致；解析變動／重複欄名、群組範圍、帶單位字串、空 duration；SOP／roles 依情境保存；輸出缺檔／截斷不可當成功 | 2～3 |
| 6. PD-02 協商與 VDM 導引 | 呈現 SourceCap→Request→Accept→PS_RDY、Discover→EnterMode→Configure 的可見前後關係，聚合值得先查的未見完成／重試／拒絕情境 | 單次正常 ACK、NAK、Reject、Cap Mismatch 不直接判故障；對照 request／response 及 trace 邊界；PDO 類型決定電流／功率解讀；錯誤／計時規則先有適用規格及測例，不猜 timeout | 3～5 |
| 7. PD-03 原生 UI 與定位 | PD 卡片顯示 SOP／角色／訊息／結果，候選直接到 Transfer，細節可到 Packet | Cap 範例 Transfer 6／8 與 Packet 150／160 對得上；5 V／0.90 A 等單位正確；沒有 Address／EP 假值；PD-only、無 PD、資料不足及定位失敗均可理解；源檔保護、重複定位不重開 | 2～3 |
| 8. EXP-02 整合與試用驗證 | 用單一發行包跑 USB2／USB3／PD，保存支援範圍與版本資格 | 混合協定 capture 的 namespace／過濾／時間核對；真實 GL3525 PD 正常／異常例、未參與調整的 USB3 例；10.50 實機重跑；真人找候選→核對證據並計總時間、錯誤方向 | 2～4，另加等待時間 |

第一個實作任務為 **EXP-01**，目的很具體：讓現有工具能安全表示並定位 Packet 與
Transfer，保留 USB2 行為。完成後按表逐片執行，不把未驗證的 LTSSM state、完整
payload 或人工作業效益塞進第一片。

### 定位層級與共存的驗收細節

`GotoUnit(3,6)` 實測可到 PD Enter Mode 起點，但 GUI 曾仍在 Packet view。
EXP-01 應先查驗既有原生介面是否能可靠設定顯示層級；如可行，用受支持介面處理。
若不能，工具需明確提示「已到對應起點，請切換 XFR／PKT 核對」，並將自動切換列為受限。
只有工程師能看到正確單位，才算該模式的端到端定位通過；不能用 API returned 結案。
不把本輪測試的座標點擊寫入產品當固定導航方式。

保留受限共存模式：偵測到非工具擁有的 LeCroy，顯示限制，不接管或關閉既有工作。
原有 deadline／失聯／晚回覆隔離及來源完整性機制應沿用；USB3／PD 不取得移除 guard
或終止不明程序的權限。記錄 API、畫面核對及完整操作時間，分開計算。

### 單檔分析的實作邊界

本輪已取得的樣本欄位可以支撐 adapter 與前後文，但不能把「前 32 筆」當成搜尋整份
trace。U3-01 需沿用現有 M2 全程路徑或有界串流保存策略，清楚揭露 cap、coverage
及過濾條件。資料不足就縮小結論，不把缺失解釋成裝置無回應。

U3-02 不先指定未知的 LTSSM 狀態、任意重試次數或時間門檻；以可核對事件組合為起點，
實作時為每條規則寫清正常反例、capture 邊界及工程師提示。若只有一個 Wake 或 Link
事件，提供上下文也不必硬湊候選。精確 state 規則只在另行證明欄位後才加入。

PD-02 也先區分事實與推測。例如「Configure 收到 NAK，之後又重新 Discover」可以
提供調查方向；「NAK 代表 GL3525 韌體故障」不能成為輸出。
若尚未取得真實故障 capture，可先完成可重跑的資料／UI 整合與依規格建立的反例測試，
產品故障與可靠度驗收維持待確認，不用官方範例替代。

EXP-02 的混合 capture、10.50 與真人驗證尚無本輪證據，不能由 Codex 模擬為通過。
資料或人員暫缺不應阻擋其他已具備輸入的技術工作，但會限制可對外宣稱的支援範圍。

## 工作量與交付範圍

一位熟悉現有 repo 的工程師估計：共用整合 2～3 人日、USB3 6～10 人日、
基本 PD＋VDM 7～11 人日、整合／試用工程工作 2～4 人日，合計 **17～28 人日**。
這是約 3.5～6 週的工程投入估計，不是承諾日期；未含收集真實故障、等待 10.50 機器／
工程師、因資格化結果產生的額外修正或硬體測試時間。

相較前次評估，本輪降低的是 PD 取資料與原生定位的風險。原生 grouping 確定可用，
因此不預留大型 PD parser／VSE 框架；整體範圍加入早期 VDM 與跨協定驗收，
尚不足以宣稱總工期一定縮短。adapter 第一片結果出來後再校正估計。

首版不含 USB4、完整 USB3 bulk／streams 語意、LTSSM 精確 state 規則、所有 PD
PPS／EPR／role swap／extended messages、電氣／Eye、USB-CV 合規或自動根因裁決。
PPS／swap 檔案這次能讀，不代表其所有規則已納入產品支援。

每片以可觀察行為、正例／正常反例／失敗邊界、原生核對及來源完整性驗收；不以測試數
或檔案產生當成產品通過。最終仍需一位工程師用陌生 trace 完成整條任務，記錄包含載入、
分析、閱讀、切換原生工具與核對的總時間，以及錯誤方向數量。

本計畫不修改 PCIe 路線，不重開既有 USB2 已驗證里程碑，也不把原有 USB2 人工／
陌生案例驗收自動升為 PASS。實作、commit／push 及產品驗收是不同工作狀態。
