# PCIe Trace 檢視報告

## 先看重點

這份報告檢查 PCIe 擷取檔（trace）`S0-Remove SD7-1350.pex`：只讀取工具輸出的前 5 筆 TLP（PCIe 封包），再抽樣與 LeCroy 畫面核對。

- **讀到了什麼：** 5 筆資料；這只是前五筆，不是整份 trace 的統計。
- **畫面核對：** 5 筆都能依封包編號及顯示內容，在 LeCroy GUI 找到相符資料。
- **測試結果：** 不知道這份 trace 對應的測試是正常或異常；本報告沒有做故障判斷。

> **簡單說：** 這證明目前工具能讀出並核對這幾筆資料，不代表裝置測試 PASS，也不代表已找出問題。

## 封包清單

| 封包編號 | LeCroy 顯示名稱 | LeCroy 畫面時間 | 工具讀取時間 |
| ---: | --- | ---: | ---: |
| 1944516 | Msg / MsgD | 4.847933004000 | 4.848 sec |
| 1944517 | Cfg / CfgRd0 | 4.847933068000 | 4.848 sec |
| 1944519 | Cfg / CfgRd0 | 4.847937356000 | 4.848 sec |
| 1944521 | Cfg / CfgRd0 | 4.847939414000 | 4.848 sec |
| 1944523 | Cfg / CfgRd0 | 4.847948900000 | 4.848 sec |

封包編號可用來在 LeCroy 中找到該列。LeCroy 畫面時間比工具輸出的時間精確；工具時間只顯示到千分之一秒（1 毫秒），因此五筆都顯示 `4.848 sec`，**不代表它們發生在同一個時間點**。

## 回看證據

- [先看 LeCroy 畫面核對](../../evidence/pcie-staircase-20260912/d1-gui-crosscheck.png)：可依上方封包編號找到對應資料。
- [查看工具原始輸出](../../evidence/pcie-staircase-20260912/d1-vendor-saved-output.log.txt)：核對工具實際印出的五筆資料。
- [查看資料底稿](observations.json)：機器可讀的記錄與來源身份。

## 本報告沒有判斷的事

- 哪份測試是 PASS 或 FAIL、裝置是否正常、或故障原因。
- 整份 trace 有多少 TLP；目前只處理工具輸出的前五筆。
- 封包 payload、request/completion 關係或可疑區段。
- LeCroy 的 `Errors detected!` 指示器不等同產品測試結果。

## 技術附錄（需要重現或核對身份時再看）

### Trace 與軟體身份

| 項目 | 值 |
| --- | --- |
| Trace 原始檔 | `S0-Remove SD7-1350.pex` |
| 本機來源路徑 | `C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex` |
| 檔案大小 | 105,224,486 bytes |
| Trace SHA-256 | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Trace 最後修改時間 (UTC) | `2026-06-11T07:12:55.2721460Z` |
| 分析軟體 | Teledyne LeCroy PCIe Protocol Analysis 13.26 Build 43 BETA |
| PETracer SHA-256 | `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| VSE script | `scripts/pcie/p0-d1-tlps.pevs` |
| Script SHA-256 | `91AAA647D24C4785A2C4418066B0D1A4BABF926E4C09B8F1EA86558EE0C507CA` |

### 原始欄位與核對方式

| 封包編號 | VSE 原始類型碼 | VSE channel 標籤 | Link width |
| ---: | --- | --- | ---: |
| 1944516 | 0xE | Downstream | x1 |
| 1944517 | 0x9 | Downstream | x1 |
| 1944519 | 0x9 | Downstream | x1 |
| 1944521 | 0x9 | Downstream | x1 |
| 1944523 | 0x9 | Downstream | x1 |

- 工具實際輸出欄位：`in.Index`, `TimeToText(in.Time)`, `GetEventName()`, `GetChannelName()`, `in.TLPType`, `in.LinkWidth`
- 工具時間來源：Vendor-formatted display text from TimeToText(in.Time); coarse seconds only. GUI timestamps are separate corroborating observations.
- GUI 另顯示封包編號 1944516, 1944517, 1944518, 1944519, 1944520, 1944521, 1944522, 1944523, 1944524, 1944525；其中 1944518, 1944520, 1944522, 1944524 是畫面上可見、但不在工具五筆輸出中的封包。下一筆畫面可見 TLP 是 1944525，只作畫面脈絡。
- VSE 原始輸出 SHA-256：`31EF4279896C216F4FA6928D275D5D3388F7FAC576A059CF4CBC5926D992EEF3`
- GUI 截圖 SHA-256：`C6FE380483ACDB27775168AA91DA630F282889DFFA1E39CC09C21BC4DFF873A0`
- 機器狀態碼：`PASS_BOUNDED` / ground truth `UNKNOWN` / diagnostic `NOT_EVALUATED` / coverage `FIRST_FIVE_TLP_RECORDS_ONLY`
- Schema：`pcie.trace-inspection-observations/v1`。這是單 trace 檢視資料，不是 finding contract、PCIe normalized event model 或 USB/PCIe 共用 schema。
