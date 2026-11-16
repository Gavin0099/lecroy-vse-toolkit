# LARGE-04 大量交易解析契約

承接 r7.2；使用者授權完成 LARGE-04，以 ASM2362-PC22-15-RND-Size-Wr-230309.pex 驗證後重新封裝。原始檔只讀，所有原生更新都在獨立工作副本。這輪不新增 PCIe 故障判斷規則。

## 資料路徑

超過原有 20,000 TLP 的輸入改走磁碟索引。此值現在用於選路，沒有把密集資料交回舊的全量記憶體解析器。

1. VSE 仍以同一組腳本輸出，增量 spool 保留完整 raw 記錄與最後 callbacks。密集路線每 Probe 的磁碟預算 1 GiB；單筆 callback 仍限 1 MiB。
2. 逐行套用既有 G1/G2/Message grammar，檢查唯一 header、END、DONE、嚴格 index 次序、筆數與首尾；每個 G2 欄位列必須逐項對上 G1，同一 Message 逐項對上 G2。缺失、重複、錯位或 runtime error 不能產生封存索引。
3. SQLite 保存完整原始列、欄位、Message、Request、Completion、最新 RequesterId/Tag 與關聯鏈終點。8 MiB page cache、暫存落盤；批次結束不代表 Request 結束。
4. nearest-preceding 同 Key 關聯完全沿用 G2b 的語義。重複 Key、孤立 Completion、split completion、未知欄位、擷取結尾均不增加 timeout/retry/root-cause 判斷。
5. 原始列與關聯完整輸出 canonical JSON／TSV，逐項串流，不先建立全量 list。既有 G3a～G3f 判斷改使用 SQLite 的 Packet／ordinal 查詢，保留相同的候選、分組與附近證據。
6. 已有原生階段／交易訂閱上限仍保留並揭露 Coverage。它們是與 TLP 全量欄位不同的觀察範圍，不能把 full TLP count 當成所有 Link／Split 記錄完整。
7. 完整原生陣列分檔封存，桌面摘要保留來源身分、計數與 SHA-256 references；工程情境重新計算時先核對並還原這些資料，不能把摘要未帶陣列當成未觀察到。

## 保護與界線

- SQLite 先寫 `.partial`，完整列交叉驗證、關聯及 integrity_check 通過才封存；來源與 display 身分由 seal 與 raw hashes 綁定。
- 取消與磁碟檢查涵蓋 ingest、關聯、JSON／TSV 輸出；原生呼叫依既有安全邊界取消。監測器不接管其他使用者 session。
- 內部完整模型的原生 capped arrays 可分檔，單份 64 MiB；桌面模型仍限 8 MiB、UI 頁面 1 MiB／20 項，沒有提高 C# 整包 JSON 容量。
- 目前既有 G3 證據圖表仍為有界投影：512 個 detector events、單一呈現區間 4,096 列及合計 8 MiB context 預算。超過時完整磁碟列／關聯保留，但報告未完成，不能截掉後宣告成功。這是呈現圖表的工程預算，不是 TLP 數量或 PCIe 規定。
- Config／階段摘要也有 8 MiB 預算；超限不發布完整分析。沒有將這些安全邊界宣稱成任意輸入容量支援。
- 原廠 Packet Range 切檔仍未採用，這輪沒有跨 `.pex` 區段重解碼；所有批次共用同一份轉換 display namespace。

## 驗證

- 以既有解析器／G2b/G3 結果為獨立對照，測批次 1、2、17 等邊界，canonical bytes 與 finding 內容相同。
- 正反例包括多筆 Completion、Tag 重用、跨批次、孤立 Completion、附近 Message、缺 END/DONE、錯列、重複 index、取消及 seal／附件身分錯誤。
- 合成 20,000／120,113／240,226 個同時未完成 Request，分別在新程序量測資源與磁碟。合成資料只證明工具解析結構，不證明原生 `.pex` 容量。
- ASM2362 必須完成原生六 Probe、全量欄位交叉驗證、關聯、Flow、桌面／報告、正確副本定位與清理；另以舊版離線解析邏輯核對已保留 raw 輸出。
- 最終 ZIP 內建 runtime 執行 ASM2362 及既有 PCIe／USB2／USB3／PD 回歸，核對原檔與 r7.1/r7.2 凍結 ZIP。真人 UX、其他版本與真實 1 GiB+ 容量另驗。
