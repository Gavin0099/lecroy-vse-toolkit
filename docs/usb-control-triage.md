# TRIAGE-1：單檔控制傳輸導引與 Automation／VSE A/B

結果：已完成本地原型，兩條資料路徑共用同一套候選分組、排序、檢查提示及離線 HTML；不需要 PASS trace、Marker 或失敗時間。尚未 commit／push，工程師實用性驗收待完成。
原因：原生 CSV 可以先做部分導引；最小 VSE 補上本次 CSV 投影未提供的狀態、request、duration 與 payload，讓更多跨事件關係可被觀察。
下一步：讓工程師依報告定位並核對候選，再以未參與調整的 FAIL capture 驗證。後續先評估 Automation 能否補足缺欄，不擴大 VSE Packet 類型或另造 Viewer。

## 使用

需要 Windows PowerShell 5.1、已註冊的 USB Protocol Suite 與 Python 3 標準函式庫。
先關閉既有 UsbSuite，並使用新的輸出目錄。

```powershell
# A：只使用 Automation，不呼叫 VSE
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\run-usb-control-triage.ps1 `
  -TracePath "C:\path\to\one-trace.usb" `
  -Output ".\results\control-triage\case01-api" -Backend Automation

# B：用最小 VSE 補充控制傳輸欄位
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\run-usb-control-triage.ps1 `
  -TracePath "C:\path\to\one-trace.usb" `
  -Output ".\results\control-triage\case01-vse" -Backend Vse
```

目前省略 Backend 時仍走 Vse；沒有靜默 fallback。A 欄位不足時可明確比較 B，
不把 A 的未知欄位補成成功、零資料或零錯誤。Output 中的 `report.html` 可直接離線開啟。
另保留 `inspection.json`、`raw-result.json`、`before.json`、`integrity.json` 及唯讀副本。
輸出含專有資料，留在本機。既有輸出、完整性失敗、native execution／計數不符均拒絕繼續。

離線重跑 B 的已保存 raw output：

```powershell
python -X utf8 -B tools/usb_control_triage.py analyze `
  --input "C:\path\to\raw-result.json" --output "C:\path\to\new-report"
```

A 的已保存 output 使用 `tools/usb_control_automation.py --input ... --output ...`。

## 工程師拿到什麼

- 第一屏突出一個主要候選，另外最多兩個次要候選收合呈現。
- 精確時間、原生 Transfer ID、Address／EP，以及可複製位置。
- 每個候選都有現象、理由、前後事件及依不同回應分岔的下一步。
- 同一請求附近反覆停止會合併，從第一筆開始，而非每次重送各占一名。
- 資料不足、靠近本次控制傳輸觀測尾端、或沒有可疑區段時，明確說明範圍；不給 USB PASS。

分析範圍是 USB2 標準 EP0 控制傳輸，不是所有 USB 類型、所有 Chapter 9／Billboard 測項。
NAK、short response 或單一資料不足旗標本身不構成故障。

LeCroy 的 VSE transfer payload 在本批包含 SETUP。程式先核對實際八個 bytes，才計算
其後的資料。最多保留 64-byte prefix，缺少的部分不補零；native 完成旗標也不等於逐筆
SETUP ACK／status handshake 已證明。規則與事前驗證計畫見
[contract](usb-control-single-trace-contract.md)。

分析與呈現分別在 `discover` 與 `render`；Automation adapter 也呼叫同一個 `discover`。
這仍是 USB2 專用模型，沒有建立跨 Bus Hound／Saleae 的通用核心。

## 驗證：本批 A/B 回放

兩條路徑都先完成搜尋，之後才對照先前 native CSV 的 Marker。位置重合不是根因或合規
判定正確的證明；原註記作者與精確 USB-CV 子測項仍未確認。

| 項目 | A：Automation CSV 投影 | B：最小 VSE |
| --- | ---: | ---: |
| 至少一個既有註記進入前三的 FAIL 檔案 | 2／6 | 6／6 |
| 前三位置覆蓋既有註記點 | 2／9 | 8／9 |
| 3 份 PASS 產生的候選區段 | 0 | 0 |
| 顯示候選未對應既有註記者 | 0 | 0 |

上述數字是本批覆核，不是假陽性率為零或陌生 trace 可靠度的證明。

| Trace | A 前三 Transfer | B 前三 Transfer（排序） | B 區段總數 |
| --- | --- | --- | ---: |
| FAIL_01 | 1386 | 1386 | 1 |
| FAIL_02 | 無 | 316 | 1 |
| FAIL_03 | 無 | 390 | 1 |
| FAIL_04 | 無 | 340 | 1 |
| FAIL_05 | 無 | 362 | 1 |
| FAIL_06 | 562 | 562、372、446 | 4 |
| PASS_01／02／04 | 無 | 無 | 0 |

FAIL_06 的 transfer 296 未進前三，不能聲稱完整覆蓋。A 的主要缺欄是完整 duration、
實際 payload／資料長度、逐筆明確完成與停止狀態，以及部分 request 欄位。空白 Cplt
保持未知，`Not Enough Data=0 bytes` 不直接變成「裝置送出零長度回應」。

A 僅代表本次測試的 CSV＋原生錯誤計數＋visible-list JSON 路線，不代表已窮盡
Automation API。`ExportUSBTransferData` 的有界測試能取得 descriptor bytes，後續可能
以按需讀取補欄來取代部分 VSE；目前尚未驗證完整組合與成本。

### 驗證明細

- 31 項新測試與既有 U01 的 14 項回歸通過；測試含合法 short response、未知欄位、
  重複事件合併、地址重設邊界、HTML escaping、輸入改動及覆寫拒絕。
- 9 份 trace 共 23,456 筆 control records，native transfer index／time／address／EP
  對上既有 CSV；全部 SETUP prefix 核對通過，來源 hash 再檢查通過。
- FAIL_01 的兩次 native 擷取正規化資料完全相等；改動檔名、Marker、已知時間 metadata
  不改變候選；平移時間不改變候選身分。
- 同一 FAIL_01 各一次 live A／B：資料取得區間 14.707／9.770 秒，包含各自 COM 開檔、
  取得資料及釋放，不含副本建立。順序、快取與單次樣本未控制，不能據此宣稱 B 普遍較快。
- 實際瀏覽器核對主要候選、次要候選收合／展開、空狀態、複製按鈕與 390px 窄版；
  沒有橫向溢出。僅有測試 web server 缺 favicon 的 404，沒有觀察到報告 script 錯誤。
- 舊 C5 排名、renderer、COM host 未修改，歷史成果與既有 dirty work 保留。

### 尚未通過的產品驗收

第 2 版曾漏掉預留的 FAIL_05，原結果保留在 `evaluation-v2.json`。查看該資料後補上
「取得表頭，再要求更多內容卻沒有資料」的關係，因此 FAIL_05 成為回歸資料，不能再算
獨立驗證。PASS_02 未用於調規則；目前沒有未參與開發的 FAIL 驗收。開發者先前也看過
第一輪含註記報告，不聲稱完全未看過答案。

工程師實際定位、排除無關候選的成本、省時效果、child packet 對應及跨 reset 裝置
連續性尚未驗收。本地原型可供檢查，不將上述缺口改寫成已通過。

## 本機成果

- [A/B 九份報告索引](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/release/index.html>)
- [FAIL_01 導引報告](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/release/Vse/fail_01/report.html>)
- [凍結程式身分及逐檔 A/B 評估](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/ab-comparison.json>)
- [LeCroy 10.40 原生能力盤點](lecroy-1040-triage-capabilities.md)

Wireshark 的摘要／分組與 Sentry 的情境聚合是設計參考，沒有移植其程式碼。
Perfetto／Ellisys viewer、其他來源 adapter 先留為後續有證據需求的候選，沒有新增依賴。
