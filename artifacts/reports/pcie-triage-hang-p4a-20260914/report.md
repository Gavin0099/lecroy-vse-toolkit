# PCIe Trace 候選檢查位置報告（Disable ASPM--Insert SD7-hang.pex）

## Trace 來源與轉換

- Original trace SHA-256 `F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6`
- Converted analysis copy SHA-256 `C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD`
- Conversion：PETracer 12.36 (Build 19) → 13.26 (Build 43) format update（PCIe Protocol Analysis 13.26 的 Update file）
- Analysis target：converted disposable copy（原始 .pex 與既有唯讀副本都沒有轉換）
- packet 編號來自轉換後的 13.26 trace；尚未證明與原始 12.36 顯示的 packet index 完全一致。

工具在 `Disable ASPM--Insert SD7-hang.pex` 的 704 筆 TLP 裡整理出 1 組候選檢查位置。每一組都附上主要定位點，也就是 LeCroy 可以直接跳過去的 packet 編號。各組依主要定位點在 trace 裡出現的先後排列，順序不代表嚴重程度。

主要定位點依固定規則選出，取這一組最早出現的 request。它只用來快速跳轉，不代表該位置比較嚴重、比較可疑，或比較接近故障原因。

這份報告只整理工具觀察到的事。這份 trace 的測試結果還沒確認（ground truth `UNKNOWN`），報告沒有判斷哪一組和故障有關。

## 報告用到的 PCIe 名詞

- `CfgRd0`，Type 0 Configuration Read request
- `SC`，Successful Completion，正常完成的 Completion status
- `Tag`，request 的編號，Completion 會帶回同一個 Tag
- `RequesterId`，送出 request 的裝置位址，格式 `bus:device.function`
- `Go to Packet`，LeCroy PETracer 的 Search > Go to Packet（Ctrl+G）
- `Segment`，同一組候選檢查位置裡位置相近的一段 packet

## 1 組候選檢查位置一覽

| Finding | 主要定位點 | 時間 | 內容 |
| --- | --- | --- | --- |
| [F001](#finding-f001) | `Packet 225043` | 9.512 sec | `CfgRd0` 同一組 key 再次出現 |

## Finding F001

### 主要定位點

`Packet 225043`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

### 觀察到什麼

9.512 sec，`Packet 225043` 的 `CfgRd0`（`Tag 6`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 225048` 再次出現（9.512 sec，`CfgRd0`）。

### 相關位置

#### Segment A（9.512 sec）

- `Packet 225043`，`CfgRd0`，`Tag 6`，Requester `000:00.0`
- `Packet 225048`，`CfgRd0`，`Tag 6`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F001`，group `G001`，candidates `C001`。

## 資料來源

- `findings.json` SHA-256 `9FD24165518826726B422804A444CD01E28989EE6EA61C04B1842F10DA282BC9`，本報告的所有觀察都來自這個檔案。
- Trace 檔名 `Disable ASPM--Insert SD7-hang.pex`，由產生報告時的命令列提供。
- Converted analysis copy SHA-256 `C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD`，由命令列提供。
- TLP 總數 704，由命令列提供，來自已驗證的 G1a 計數。
