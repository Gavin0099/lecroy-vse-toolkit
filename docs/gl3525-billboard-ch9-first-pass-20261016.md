# GL3525 Billboard Chapter 9 最新 trace 初步分析

結果：9 份 trace 全部能以現有 LeCroy 自動化介面讀取；既有 U01 探針也在 PASS_01／FAIL_01 通過。6 份 FAIL 均有 descriptor 請求相關註記，可據此回到原生 trace 檢查。
原因：這批原生 transfer 匯出顯示 H／F 速率標籤與 EP0 控制請求；舊 USB3 主分析器在 PASS_01 正常執行後取得 0 筆目標事件，因此無法直接產生其既有比較報告。
下一步：先查 FAIL_01 transfer 1386 與 FAIL_06 的未完成請求，再對照其餘 descriptor 註記；需要取得原生 SETUP／data／status 與 packet 對應後才判讀原因。

本次是新資料的本地可用性與原生觀測分析，未新增產品 decoder 或 Chapter 9 合規判定器。

## 來源與標籤

- 來源目錄 `C:\Users\reiko\Desktop\1016\GL3525-OVY1L_Billboarda-CV_test_issue`。
- 2026-10-16 執行；9 份不同 SHA-256，合計 235,976,744 bytes；FAIL 6 份、PASS 3 份。
- 使用者確認依檔名辨識 PASS／FAIL；相同韌體、相同測試步驟與精確 USB-CV 子測項尚未確認。內嵌 Marker 是 trace 既有註記，其作者與產生來源未確認。
- runtime：USB Protocol Suite 10.40 (Build 6309)；repo HEAD `7725f5b86c0208d92f96347122ae0dff4a0e6240`。
- 全程只開啟新建的唯讀 `.usb` 副本；9 份來源與副本前後 SHA-256、大小、mtime／readonly 檢查通過。未開啟原目錄中的 `.usb.tmp` 快取。

## 9 份檔案的原生觀測

| 檔案尾碼 | Packet 數 | 原生可見 transfer 列數 | 速率標籤 | trace 既有註記 |
| --- | ---: | ---: | --- | --- |
| fail_01 | 894,015 | 1,497 | H, F | Time Stamp: GetConfigDesc() fail |
| fail_02 | 1,205,747 | 3,075 | H, F | Time Stamp: GetStringDescFail |
| fail_03 | 1,284,232 | 3,074 | H, F | Time Stamp: GetOtherSpeedDesc() fail |
| fail_04 | 1,152,060 | 3,075 | H, F | Time Stamp: GetDesc() fail |
| fail_05 | 1,276,520 | 3,075 | H, F | Time Stamp: GetBosDesc() fail |
| fail_06 | 2,364,565 | 673 | H, F | Time Stamp: GetStrinDesc() fail; Time Stamp: GetBosDesc() fail; Time Stamp: GetBosDesc() fail; Time Stamp: GetConfigDesc() fail |
| pass_01 | 563,789 | 2,846 | H, F | 未匯出 Marker |
| pass_02 | 711,289 | 3,066 | H, F | 未匯出 Marker |
| pass_04 | 620,103 | 3,075 | H, F | 未匯出 Marker |

## FAIL 的定位點

| 檔案 | 原生 transfer ID | 時間（秒） | Address／EP | 原生 request／descriptor | 原生資料旗標 |
| --- | ---: | --- | --- | --- | --- |
| fail_01 | 1386 | 35.611541400 | 13／0 | GET_DESCRIPTOR／CONFIGURATION type, Index 0／0x0000 | Cplt=NO; Not Enough Data=0 bytes |
| fail_02 | 316 | 20.423089666 | 5／0 | GET_DESCRIPTOR／STRING type, Index 4／Language ID 0x0409 | Not Enough Data=0 bytes |
| fail_03 | 390 | 24.096624166 | 5／0 | GET_DESCRIPTOR／OTHER_SPEED_CONFIGURATION type／0x0000 | Not Enough Data=0 bytes |
| fail_04 | 340 | 17.710384116 | 5／0 | GET_DESCRIPTOR／DEVICE type／0x0000 | Not Enough Data=0 bytes |
| fail_05 | 362 | 22.002367282 | 5／0 | GET_DESCRIPTOR／BOS type／0x0000 | Not Enough Data=0 bytes |
| fail_06 | 296 | 21.846086782 | 5／0 | GET_DESCRIPTOR／STRING type, Index 6／Language ID 0x0409 | Not Enough Data=0 bytes |
| fail_06 | 372 | 27.608155682 | 5／0 | GET_DESCRIPTOR／BOS type／0x0000 | Not Enough Data=0 bytes |
| fail_06 | 446 | 33.191925582 | 12／0 | GET_DESCRIPTOR／BOS type／0x0000 | Not Enough Data=0 bytes |
| fail_06 | 562 | 40.351786032 | 19／0 | GET_DESCRIPTOR／CONFIGURATION type, Index 0／0x0000 | Cplt=NO; Not Enough Data=0 bytes |

`Cplt=NO` 表示 LeCroy 在該 transfer 的原生欄位標示未完成。`Not Enough Data=0 bytes` 保留原生顯示文字；不能單獨等同裝置實際送出零長度封包。空白 Cplt 也不自動推論正常。transfer ID 是 transfer 層索引，不能當 packet number。

除上述註記列，額外的資料不足列也全部保存在 summary.json。PASS_04 在 19.552701132 秒的 transfer 226 同樣有 `GET_DESCRIPTOR / CONFIGURATION type, Index 1 / Not Enough Data=0 bytes`；FAIL_02–06 也有相同 request 類型與旗標。因此這類旗標單獨不能區分 PASS／FAIL，還需檢查請求條件與實際回應。

## 現有功能可沿用的範圍

| 現有功能 | 本次實測 | 能回答的問題 |
| --- | --- | --- |
| 來源保護與 COM 讀檔 | 9／9 可開啟；完整性檢查通過 | 這批檔案是否能安全讀取 |
| U01 packet／transaction／transfer 探針 | PASS_01、FAIL_01 各 7 種 selection 完成，14／14 transport consistent | 指定 selection 的 callback 數與有界 metadata 樣本 |
| 原生 CSV 匯出 | 9／9 transfer CSV、起始 packet CSV | 原生控制請求名稱、時間、地址、descriptor 類型與註記 |
| 舊 M2／DEMO USB3 主分析器 | PASS_01 腳本正常 DONE，三類目標事件均為 0；wrapper 停止 | 本次不能直接用它的 USB3 時間線比較；FAIL_01 未由該 wrapper 執行 |
| C5 異常區間排名／既有 HTML | 未執行 | 其訊號前提未建立，不能宣稱套用成功 |
| Chapter 9／Billboard descriptor 合規、根因 | 尚未建立 | 仍需原始 payload、status、packet 對應與適用測項 |

## 驗證

| selection | PASS_01 callbacks | FAIL_01 callbacks |
| --- | ---: | ---: |
| packet-default | 563,789 | 894,015 |
| packet-crc-off | 563,789 | 894,015 |
| packet-crc-on | 563,789 | 894,015 |
| transaction-all | 29,986 | 253,422 |
| transfer-default | 2,846 | 1,497 |
| transfer-complete | 2,846 | 1,496 |
| transfer-incomplete | 0 | 1 |

- 每種 selection 只保存各自層級索引 0–200 的 metadata 樣本；callbacks 為該選擇的遍歷計數，並非 payload／status 正確性驗證。空樣本不證明事件不存在。
- PASS_01／FAIL_01 的 native packet count 與 U01 packet-default callbacks 一致；原生 transfer CSV 列數與 U01 transfer-default callbacks 一致；Cplt=NO 列數分別與 incomplete selection 的 0／1 一致。這是同一 LeCroy decoder 的路徑交叉核對。
- CRC-on／off 計數相同不證明沒有 CRC 問題。
- Native ExportToCsv 未變更 display options；隱藏單位可能不匯出，完整 capture coverage 未資格化。
- 本次沒有產品程式行為變更，未新增單元測試；可用性證據來自實際 runtime 與輸出／來源身分核對。

## 證據與限制

- [完整 summary JSON](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard/summary.json>)。
- [來源與副本完整性](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard/source-integrity.json>)。
- 原生 CSV、evidence.json 與唯讀副本位於 `C:\Users\reiko\.codex\visualizations\2026\10\16\01a14297-966e-7b51-b3e6-572fecb51b9e\gl3525-billboard\native-inventory`。
- U01 計畫、腳本、14 組 result／assessment／integrity 與 lifecycle logs 位於 `C:\Users\reiko\.codex\visualizations\2026\10\16\01a14297-966e-7b51-b3e6-572fecb51b9e\gl3525-billboard` 下的 `pass01-*`、`fail01-*`。
- 原生匯出依本機 USBAnalyzerAutomationManual.pdf §7.1.10／§7.2.3（PDF 126／132–134）使用 GetPacketsCount 與 ExportToCsv；沒有改變 decoder 或重建 transfer grouping。
- 這是本機證據包；含專有 trace 副本，未加入 Git，也未上傳。
- 不宣稱裝置或韌體根因、USB-CV 合規結果、所有資料旗標都是故障、精確 device identity、跨 capture address 對應或同韌體同流程。
- 本地分析完成；未 commit、push、PR 或 merge。
