# PCIe Config 與 UR 證據契約

此版從已匯入的 PCIe 案件補抽。原生工作使用現有唯讀副本、排他流程與 Packet namespace。標準解碼和九筆 Memory Read 的 UR 是第一版範圍。BAR 未知時僅呈現地址。

## 介面

- 原生工作輸出 `pcie.config-ur-observations/v1`。`events` 依 Packet 升冪且唯一。即使額外欄位未知，也保存已驗證的 non-posted Request 和 Completion metadata，以曝露 Tag 重用。Read／Write 的 `device_id` 是目的 BDF。Completion 的同欄位是 Completer ID。Memory Request 的同欄位保留 null。
- `register` 是 Config byte offset。地址、寫入 DWORD、BE、長度、Byte Count、Lower Address 以數字表示。null 保留未知。Memory Success Completion 可能分段，`payload_bytes` 是本封包有效 payload 長度。Legacy non-Flit 0 Byte Count 及 0 Length 的 wire 編碼需先由擷取層正規化，無可靠欄位則為 null。
- `evidence[].fields` 說明該原生來源驗證了哪些欄位。檔案名稱相對於此次補抽工作目錄，來源原始資料可用雜湊及行定位。時間無原生支撐時用 null。Metadata fallback 可使用既有已核對的顯示時間字串。
- `link_downs` 只放已核對的 Link Down Packet。以已觀察的區間隔離 pending；`epoch` 是切點序數，代表觀察分區。物理 Link 或 Device 身分未知時不從 BDF 延伸。邊界不完整或原始 stream 受限時用 Coverage 欄位表示，缺證據不能升格為無回覆。
- 離線分析由 `pcie_config_ur_analysis.analyze(observations)` 產出 `pcie.config-ur-evidence/v1`。列出 Config Request 和對應到 Memory Request 的 UR／CA，另保留未配對或狀態未確認的 Completion。列 ID 以 `p` 加原 Request Packet 組成。後續讀回帶回原讀 Request、Completion 和同區間／跨區間。跨區間的回讀與暫存器名稱只作同 BDF 比對線索，寫入欄位須有同區間的標準定義。
- Cap pointer、Capability ID 與欄位位置可建立暫存器身分。無對應定義時用 `UNKNOWN`。寫入只宣告觀察到的 request intent，`write_effect` 保持 `NOT_ESTABLISHED`。沒有已驗證 BAR 映射時，Memory 列用 `BAR_UNKNOWN`。
- 依記憶體地址和讀取長度彙整 UR。每組有 `address`、`byte_length`、`count`、`row_ids`、`bursts`。觀察區間由原生時間相隔超過 100 ms 或 Link Down 切點分開。未知時間另列。分組僅用於呈現。單筆 Request／Completion 關聯和每次 UR 都保留。
- UI 和匯出共用分析結果。每次補抽目錄保存 `evidence.json` 與該次原始證據。C# 用 controller IPC `config_ur_run`、`config_ur_navigate`。後者帶 `case_id`、`row_id`、`target`（`request`、`completion`、`read_request` 或 `read_completion`）。Controller 只接受已發布結果中的來源綁定定位目標。不接受由 UI 提供自由 Packet index 或檔名。C# 工作狀態從 `status.json` 的 `config_ur` 讀取，ready 後載入其 `index` 相對於 case folder 的檔案。
- 獨立 fixture 和真實 1329 都須驗證寫入、BE、回覆、地址、回讀、能力鏈與時間分群。另測故障、未知 framing、跨 Link Down、同 Tag 競爭與取消。即使補抽失敗，案件仍可查看。

JSON Schema 見 [pcie-config-ur-evidence.v1.json](../schemas/pcie-config-ur-evidence.v1.json)。首版以 [1329 fixture](../tests/fixtures/pcie-config-ur-1329.json) 的原始資料與已另核對的預期結果為共同測資。
