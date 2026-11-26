# r7.4 PCIe 桌面索引分析與進度存取修正版

解壓完整資料夾後執行 `USBTraceTriage.exe`。內含 Python 與 SQLite runtime，仍需本機 PETracer／USB Protocol Suite。原始 trace 只讀，舊格式仍在工作副本自動轉換。

## 此次修正與更新方式

舊 r7.3 若出現 `worker.json Permission denied`，表示工具讀取程序間進度紀錄失敗，不能據此判定 Trace 或裝置故障。新版對短暫的 Windows 存取／分享衝突採最多 2 秒重試；持續拒絕、損壞的 JSON 或未完成尾端仍會明確停止發布。請保留原工作資料夾。若舊作業留下 PETracer，先確認原生工作已結束，避免接管其他人的 session。

請關閉舊版工具，將新版 ZIP 完整解壓至新的資料夾，再執行其中的 `USBTraceTriage.exe`；不要只替換 EXE。新版保留 r7.3 原封裝與原始 Trace。

大量資料改為最多 256 筆一批的 VSE 文字回報。每筆格式、順序、尾筆及原有計數／逐列交叉核對維持不變；單次 callback 的 1 MiB 上限仍適用。磁碟檢查改成每 1 MiB 寫入額度或每秒重新查詢，flush 前再檢查，避免逐筆查詢磁碟的開銷。分析中顯示已輸出文字列與 bytes；文字列含標頭，不能直接當作已驗證 TLP 筆數。獨立 TLP 計數與尾端核對仍分開顯示。

完整 JSON 證據以一筆有界紀錄為單位編碼，保留逐位元一致的欄位排序與格式；巢狀大量 Completion 仍串流處理。逐列欄位交叉核對也只解碼一次參考列，全部比對條件維持不變。沒有提高資料上限、移除證據匯出或略過完整性檢查。

交易關聯匯出以 SQL JOIN 順序讀取 Request 與 Completion，避免逐組重複查詢相同欄位。單筆交易最多 16 個 Completion 可合併編碼，超過仍串流；這是記憶體處理方式，不是 Completion 數量上限。缺少欄位仍報錯，不會因 JOIN 靜默略掉交易。

## 大量交易處理

超過 20,000 TLP 時自動使用 SQLite 索引；此數字是選路門檻，已不會單憑這個數字拒絕分析。所有列仍須通過獨立計數、G1/G2/Message 逐列一致性與尾端完成檢查。Request／Completion 狀態跨解析批次延續，不因批次結束而推定 timeout 或 missing Completion。

工作資料夾中的 `analysis/transactions.sqlite` 保存完整列、欄位與 Request／Completion 關聯；`verified-fields/fields.json`、`verified-messages/messages.json` 保留完整標準化欄位資料。桌面不再等待重複的列／角色／關聯 JSON 與 TSV 全量匯出；所有列的一致性、結尾、交易關聯及候選檢查仍執行，不是抽樣或省略分析。SQLite commit 每 4,096 列一次，cache 仍固定 8 MiB；這是磁碟交易批次，不是封包上限。

需要完整附加診斷檔時，在解壓後的 `USB-Trace-Triage` 資料夾執行（將路徑換成此次工作的 `analysis`）：

```powershell
.\runtime\python.exe .\tools\pcie_dense_exports.py --root "C:\工作資料夾\analysis"
```

這會從已核對 SHA 的唯讀索引產生 `verified-rows/rows.json`、兩份 TSV，以及 `report/stages/associations.json`、`roles.json`、`orphan_completions.json`；不需重開 PETracer，也不讀寫原始 `.pex`。已存在的檔案不會覆寫；需要另一份輸出可加 `--output "C:\新的診斷資料夾"`。`diagnostic-exports.json` 記錄來源／副本／索引 SHA 與每份輸出完整性。CLI 原有完整匯出模式保留，這些關聯仍不代表完整 Split Mapping 或 PCIe PASS。

原生 Link／LTSSM、Packet／Link／Split 交易擷取仍有原有上限；Coverage 會揭露已保留筆數及缺口。完整 TLP 欄位分析完成，不等於所有原生層級均完整覆蓋。

## 畫面與完整證據

工作區仍先顯示最多三個流程目標。大量原生陣列改為 `analysis/model-evidence-*/` 的 JSON 附件，桌面摘要保留筆數與來源 hash，HTML／Markdown 列出附件入口。摘要沒有攜帶陣列，不表示 trace 沒有那些事件。工程情境更新會先核對並還原附件，再重新計算。

按「匯出報告」會同時建立必要的證據附件資料夾；分享時請將報告與該資料夾一併提供。完整 TLP JSON／TSV 與 SQLite 則仍在工作資料夾，可另外提供給需要逐列覆核的工程師。

## 工程安全預算

- 原始 Probe／完整 JSON 證據：每檔 1 GiB 磁碟預算；單 callback 1 MiB。
- SQLite cache：8 MiB；全量交易與未完成 Request 狀態落盤。
- 原生 capped arrays 附件：每份 64 MiB；桌面摘要仍為 8 MiB，UI 頁面仍為 1 MiB／20 項。
- 既有 G3 呈現圖表：最多 512 個 detector events，單一顯示跨度 4,096 列、context 合計 8 MiB。超過時保留完整索引／關聯但停止發布完成報告，不會靜默裁切後當成成功。
- Config／階段摘要、程序 private bytes、磁碟保留空間、原生逾時與 ownership 保護仍適用；詳見大檔防護說明。

這些是工具資源預算，均不屬於 PCIe 規範。完整索引已建立而呈現預算不足時，錯誤會說明停止階段；請保留工作資料夾，不要只調高上限。

ASM2362 120,113 TLP 的實測結果與最終封裝身分見交付報告。合成大量資料、這一份約 156.4 MiB trace 的通過，都不能當成真實 1 GiB／2 GiB 原生容量或陌生 Trace 判斷正確率。
