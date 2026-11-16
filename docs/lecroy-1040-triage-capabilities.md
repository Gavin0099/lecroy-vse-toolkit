# LeCroy 10.40：Automation 優先的資料能力盤點

本機版本為 **10.40 (Build 6309)**。本輪只讀受保護的 trace 副本，不錄製、不儲存 trace，
不改 decoder。線上 10.50 文件不直接等於 10.40 runtime 已驗證。

| 能力 | 本機機器介面 | 實際結果 | 仍未證明 |
| --- | --- | --- | --- |
| 讀檔及 packet 數 | `OpenFile`、`GetPacketsCount` | 9 份 trace 可讀 | 格式獨立 parser |
| 原生 transfer 表格 | `ExportToCsv(3,-1,-1)` | 9 份 CSV，可做 A 的部分導引 | 空白欄位不等於成功或零值；display 可能隱藏單位 |
| Error Summary 候選來源 | `AnalyzerErrors(type)`、collection `Count` | FAIL_01 的 14 類都返回 0 | 沒有正例，非空 Item 與每類語意未資格化；未宣稱完全等同 GUI Summary |
| 定位 | `GotoTime(ns)`、`GotoUnit(level,index)` | 時間與 transfer 1386 呼叫返回 | GUI 畫面實際落點未人工確認 |
| Transaction＋Packet 匯出 | `ExportTransactionsWithPacketsToCsv(0,10)` | 有界呼叫寫出 CSV | transfer→transaction→packet membership 尚未資格化 |
| 可見清單 JSON | `ExportVisibleTraList(path)` | 本次 894,015 筆，全部只有 index／level／name，level=0 | 這個 profile 沒有 request／timestamp／payload；其他 view/profile 未窮盡 |
| 按範圍的 transfer data | `ExportUSBTransferData` | 第一筆指定 transfer 匯出 18 bytes，對上 VSE 的 descriptor response | 多筆邊界、全批效能、SETUP／status 補欄未驗證 |
| 最小 VSE context | `_XFER`／`_X_CONTROL` | 9 份 23,456 records，另有 repeat | 不是完整 Chapter 9 驗證器或實體 handshake 證明 |
| Traffic Summary／Navigator 圖形／LTSSM View | 10.50 官方 Reports 有列出 | 本輪只驗證上述相關機器介面 | 沒有證明 GUI 報表的完整匯出，也不聲稱 API 不存在 |

最有產品意義的反例是：FAIL_01 查詢的 Error counts 全是 0，但 control records 有
Completed=0 的 configuration request。錯誤摘要可以提供背景，仍需跨事件關聯。

`ExportVisibleTraList` 也不必等升級到 10.50：本機已可呼叫。然而本次輸出是可見單位
索引，不是完整結構化 protocol 資料。啟動／開檔／JSON 匯出合計 47.699 秒，檔案
82,027,165 bytes；單一 profile／單次量測，不能推論所有 Automation 都慢或無用。

`ExportUSBTransferData` 證明 bytes 可由另一條 Automation 路徑取得，所以本次 A/B 的
結論是「已測試的 A 投影缺欄，B 有補充價值」，不是「只有 VSE 才能取得資料」。
後續應先驗證按需 Automation 補欄，再決定是否縮減 VSE，而非擴大 Packet 類型。

## 來源與證據

本機 `USBAnalyzerAutomationManual.pdf`：PDF 128–129 為 AnalyzerErrors，130–131 為
GotoTime／GotoUnit，132–134 為 CSV，143–144 為 transaction＋packet 匯出，150 為
ExportVisibleTraList，208 為 Errors collection。GotoTime 單位是奈秒；GotoUnit 的 3
為 transfer。Automation error_type 與 VSE error bitmap 是不同編號空間，不自行互換。

- [14 類錯誤計數及定位 probe](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/native-capability-1040/probe.json>)
- [JSON／data 匯出 probe](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/automation-a-spike/probe.json>)
- [全部 JSON key／level 檢查](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/automation-a-spike/visible-json-shape.json>)

[Wireshark Expert Information](https://www.wireshark.org/docs/wsug_html_chunked/ChAdvExpert.html)
支持摘要作為調查起點、保留原始位置的分工。
[LeCroy 10.50 Reports](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/reports)
用於確認原生 GUI 功能類別；10.40 執行能力以上述本機觀測為準。
[官方 Automation 文件](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/primary-dual-interface-for-trace)
另列出各匯出介面。使用者研究中的其餘產品保留為設計參考，本輪沒有驗證其全部現況或整合成本。
