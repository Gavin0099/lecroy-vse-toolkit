# PCIe Trace 候選檢查位置報告（S0-Remove SD7-1350.pex）

工具在 `S0-Remove SD7-1350.pex` 的 938 筆 TLP 裡整理出 16 組候選檢查位置。每一組都附上主要定位點，也就是 LeCroy 可以直接跳過去的 packet 編號。各組依主要定位點在 trace 裡出現的先後排列，順序不代表嚴重程度。

主要定位點依固定規則選出，取這一組最早出現的 request。它只用來快速跳轉，不代表該位置比較嚴重、比較可疑，或比較接近故障原因。

這份報告只整理工具觀察到的事。這份 trace 的測試結果還沒確認（ground truth `UNKNOWN`），報告沒有判斷哪一組和故障有關。

## 報告用到的 PCIe 名詞

- `MRd(32)`，32-bit Memory Read request
- `CfgRd0`，Type 0 Configuration Read request
- `CfgWr0`，Type 0 Configuration Write request
- `Cpl`，沒有帶資料的 Completion
- `UR`，Unsupported Request，Completion status 的一種
- `SC`，Successful Completion，正常完成的 Completion status
- `ERR_COR`，Correctable Error Message，裝置回報可更正錯誤的 message
- `SLOTPOWERLIMIT`，Set Slot Power Limit message
- `Tag`，request 的編號，Completion 會帶回同一個 Tag
- `RequesterId`，送出 request 的裝置位址，格式 `bus:device.function`
- `Go to Packet`，LeCroy PETracer 的 Search > Go to Packet（Ctrl+G）
- `Segment`，同一組候選檢查位置裡位置相近的一段 packet

## 16 組候選檢查位置一覽

| Finding | 主要定位點 | 時間 | 內容 |
| --- | --- | --- | --- |
| [F001](#finding-f001) | `Packet 1944517` | 4.848 sec、5.883 sec | `CfgRd0` 同一組 key 再次出現；附近有 `SLOTPOWERLIMIT` |
| [F002](#finding-f002) | `Packet 1944519` | 4.848 sec、5.883 sec | `CfgRd0`、`CfgWr0` 同一組 key 再次出現；附近有 `SLOTPOWERLIMIT` |
| [F003](#finding-f003) | `Packet 1944521` | 4.848 sec、5.880 sec | `CfgRd0`、`CfgWr0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR`、`SLOTPOWERLIMIT` |
| [F004](#finding-f004) | `Packet 1944523` | 4.848 sec、5.883 sec | `CfgRd0`、`CfgWr0` 同一組 key 再次出現；附近有 `SLOTPOWERLIMIT` |
| [F005](#finding-f005) | `Packet 1944525` | 4.848 sec、4.853 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR`、`SLOTPOWERLIMIT` |
| [F006](#finding-f006) | `Packet 1944527` | 4.848 sec、4.853 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR`、`SLOTPOWERLIMIT` |
| [F007](#finding-f007) | `Packet 1944531` | 4.848 sec、4.853 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR`、`SLOTPOWERLIMIT` |
| [F008](#finding-f008) | `Packet 1944533` | 4.848 sec、4.853 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR`、`SLOTPOWERLIMIT` |
| [F009](#finding-f009) | `Packet 1944535` | 4.848 sec、5.880 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR` |
| [F010](#finding-f010) | `Packet 1944537` | 4.848 sec、5.880 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR` |
| [F011](#finding-f011) | `Packet 1944539` | 4.848 sec、5.880 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR` |
| [F012](#finding-f012) | `Packet 1944547` | 4.848 sec、5.880 sec | `CfgRd0` 同一組 key 再次出現；`MRd(32)` 收到 `UR`；附近有 `ERR_COR` |
| [F013](#finding-f013) | `Packet 1944549` | 4.848 sec、5.883 sec | `CfgRd0` 同一組 key 再次出現 |
| [F014](#finding-f014) | `Packet 1944553` | 4.848 sec、5.883 sec | `CfgRd0` 同一組 key 再次出現 |
| [F015](#finding-f015) | `Packet 1944555` | 4.848 sec、5.883 sec | `CfgRd0` 同一組 key 再次出現 |
| [F016](#finding-f016) | `Packet 1944557` | 4.848 sec、5.883 sec | `CfgRd0` 同一組 key 再次出現 |

## Finding F001

### 主要定位點

`Packet 1944517`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1944559`
- Segment C，`Packet 2093601`

### 觀察到什麼

4.848 sec，`Packet 1944517` 的 `CfgRd0`（`Tag 8`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944559` 再次出現（4.848 sec，`CfgRd0`）。

4.848 sec，`Packet 1944559` 的 `CfgRd0`（`Tag 8`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093601` 再次出現（5.883 sec，`CfgRd0`）。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944517`，`CfgRd0`，`Tag 8`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.848 sec）

- `Packet 1944559`，`CfgRd0`，`Tag 8`，Requester `000:00.0`

#### Segment C（5.883 sec）

- `Packet 2093601`，`CfgRd0`，`Tag 8`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `SLOTPOWERLIMIT` 和 這裡的 request 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 3 個 Segment 前後相隔約 149,084 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F001`，group `G001`，candidates `C001`、`C019`。

## Finding F002

### 主要定位點

`Packet 1944519`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1944563`
- Segment C，`Packet 2093615`

### 觀察到什麼

4.848 sec，`Packet 1944519` 的 `CfgRd0`（`Tag 14`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944563` 再次出現（4.848 sec，`CfgWr0`）。

4.848 sec，`Packet 1944563` 的 `CfgWr0`（`Tag 14`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093615` 再次出現（5.883 sec，`CfgRd0`）。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944519`，`CfgRd0`，`Tag 14`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.848 sec）

- `Packet 1944563`，`CfgWr0`，`Tag 14`，Requester `000:00.0`

#### Segment C（5.883 sec）

- `Packet 2093615`，`CfgRd0`，`Tag 14`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `SLOTPOWERLIMIT` 和 這裡的 request 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 3 個 Segment 前後相隔約 149,096 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F002`，group `G002`，candidates `C002`、`C020`。

## Finding F003

### 主要定位點

`Packet 1944521`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093086`

### 觀察到什麼

4.848 sec，`Packet 1944521` 的 `CfgRd0`（`Tag 0`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944543` 再次出現（4.848 sec，`CfgRd0`）。

4.848 sec，`Packet 1944543` 的 `CfgRd0`（`Tag 0`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944567` 再次出現（4.848 sec，`CfgWr0`）。

4.848 sec，`Packet 1944567` 的 `CfgWr0`（`Tag 0`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093086` 再次出現（5.880 sec，`MRd(32)`）。

5.880 sec，`Packet 2093086` 的 `MRd(32)` request（`Tag 0`）收到 `Packet 2093088` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）
- `Packet 2093072`，`ERR_COR`（5.880 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944521`，`CfgRd0`，`Tag 0`，Requester `000:00.0`
- `Packet 1944543`，`CfgRd0`，`Tag 0`，Requester `000:00.0`
- `Packet 1944567`，`CfgWr0`，`Tag 0`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（5.880 sec）

- `Packet 2093086`，`MRd(32)`，`Tag 0`，Requester `000:00.0`
- `Packet 2093088`，`Cpl`，`Tag 0`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 2093072`，`ERR_COR`，附近的 message

`Packet 2093086` 和 `Packet 2093088` 的對應，已在 LeCroy Split Transaction 畫面核對一致（`Split Tra 29`）。

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR`、`SLOTPOWERLIMIT` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 148,567 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F003`，group `G003`，candidates `C003`、`C012`、`C021`、`C030`。

## Finding F004

### 主要定位點

`Packet 1944523`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1944571`
- Segment C，`Packet 2093652`

### 觀察到什麼

4.848 sec，`Packet 1944523` 的 `CfgRd0`（`Tag 5`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944571` 再次出現（4.848 sec，`CfgWr0`）。

4.848 sec，`Packet 1944571` 的 `CfgWr0`（`Tag 5`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093652` 再次出現（5.883 sec，`CfgRd0`）。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944523`，`CfgRd0`，`Tag 5`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.848 sec）

- `Packet 1944571`，`CfgWr0`，`Tag 5`，Requester `000:00.0`

#### Segment C（5.883 sec）

- `Packet 2093652`，`CfgRd0`，`Tag 5`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `SLOTPOWERLIMIT` 和 這裡的 request 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 3 個 Segment 前後相隔約 149,129 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F004`，group `G004`，candidates `C004`、`C022`。

## Finding F005

### 主要定位點

`Packet 1944525`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1945005`

### 觀察到什麼

4.848 sec，`Packet 1944525` 的 `CfgRd0`（`Tag 11`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1945005` 再次出現（4.853 sec，`MRd(32)`）。

4.853 sec，`Packet 1945005` 的 `MRd(32)` request（`Tag 11`）收到 `Packet 1945008` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）
- `Packet 1945029`，`ERR_COR`（4.853 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944525`，`CfgRd0`，`Tag 11`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.853 sec）

- `Packet 1945005`，`MRd(32)`，`Tag 11`，Requester `000:00.0`
- `Packet 1945008`，`Cpl`，`Tag 11`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 1945029`，`ERR_COR`，附近的 message

`Packet 1945005` 和 `Packet 1945008` 的對應，已在 LeCroy Split Transaction 畫面核對一致（`Split Tra 22`）。

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR`、`SLOTPOWERLIMIT` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 483 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F005`，group `G005`，candidates `C005`、`C023`。

## Finding F006

### 主要定位點

`Packet 1944527`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1945011`

### 觀察到什麼

4.848 sec，`Packet 1944527` 的 `CfgRd0`（`Tag 1`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1944551` 再次出現（4.848 sec，`CfgRd0`）。

4.848 sec，`Packet 1944551` 的 `CfgRd0`（`Tag 1`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1945011` 再次出現（4.853 sec，`MRd(32)`）。

4.853 sec，`Packet 1945011` 的 `MRd(32)` request（`Tag 1`）收到 `Packet 1945013` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）
- `Packet 1945029`，`ERR_COR`（4.853 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944527`，`CfgRd0`，`Tag 1`，Requester `000:00.0`
- `Packet 1944551`，`CfgRd0`，`Tag 1`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.853 sec）

- `Packet 1945011`，`MRd(32)`，`Tag 1`，Requester `000:00.0`
- `Packet 1945013`，`Cpl`，`Tag 1`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 1945029`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR`、`SLOTPOWERLIMIT` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 486 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 1945011` 和 `Packet 1945013` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F006`，group `G006`，candidates `C006`、`C015`、`C024`。

## Finding F007

### 主要定位點

`Packet 1944531`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1945016`

### 觀察到什麼

4.848 sec，`Packet 1944531` 的 `CfgRd0`（`Tag 7`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1945016` 再次出現（4.853 sec，`MRd(32)`）。

4.853 sec，`Packet 1945016` 的 `MRd(32)` request（`Tag 7`）收到 `Packet 1945018` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）
- `Packet 1945029`，`ERR_COR`（4.853 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944531`，`CfgRd0`，`Tag 7`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.853 sec）

- `Packet 1945016`，`MRd(32)`，`Tag 7`，Requester `000:00.0`
- `Packet 1945018`，`Cpl`，`Tag 7`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 1945029`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR`、`SLOTPOWERLIMIT` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 487 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 1945016` 和 `Packet 1945018` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F007`，group `G007`，candidates `C007`、`C025`。

## Finding F008

### 主要定位點

`Packet 1944533`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 1945021`

### 觀察到什麼

4.848 sec，`Packet 1944533` 的 `CfgRd0`（`Tag 13`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 1945021` 再次出現（4.853 sec，`MRd(32)`）。

4.853 sec，`Packet 1945021` 的 `MRd(32)` request（`Tag 13`）收到 `Packet 1945023` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 1944516`，`SLOTPOWERLIMIT`（4.848 sec）
- `Packet 1945029`，`ERR_COR`（4.853 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944533`，`CfgRd0`，`Tag 13`，Requester `000:00.0`
- `Packet 1944516`，`SLOTPOWERLIMIT`，附近的 message

#### Segment B（4.853 sec）

- `Packet 1945021`，`MRd(32)`，`Tag 13`，Requester `000:00.0`
- `Packet 1945023`，`Cpl`，`Tag 13`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 1945029`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR`、`SLOTPOWERLIMIT` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 490 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 1945021` 和 `Packet 1945023` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F008`，group `G008`，candidates `C008`、`C026`。

## Finding F009

### 主要定位點

`Packet 1944535`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093063`

### 觀察到什麼

4.848 sec，`Packet 1944535` 的 `CfgRd0`（`Tag 3`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093063` 再次出現（5.880 sec，`MRd(32)`）。

5.880 sec，`Packet 2093063` 的 `MRd(32)` request（`Tag 3`）收到 `Packet 2093065` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 2093072`，`ERR_COR`（5.880 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944535`，`CfgRd0`，`Tag 3`，Requester `000:00.0`

#### Segment B（5.880 sec）

- `Packet 2093063`，`MRd(32)`，`Tag 3`，Requester `000:00.0`
- `Packet 2093065`，`Cpl`，`Tag 3`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 2093072`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 148,530 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 2093063` 和 `Packet 2093065` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F009`，group `G009`，candidates `C009`、`C027`。

## Finding F010

### 主要定位點

`Packet 1944537`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093071`

### 觀察到什麼

4.848 sec，`Packet 1944537` 的 `CfgRd0`（`Tag 9`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093071` 再次出現（5.880 sec，`MRd(32)`）。

5.880 sec，`Packet 2093071` 的 `MRd(32)` request（`Tag 9`）收到 `Packet 2093075` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 2093072`，`ERR_COR`（5.880 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944537`，`CfgRd0`，`Tag 9`，Requester `000:00.0`

#### Segment B（5.880 sec）

- `Packet 2093071`，`MRd(32)`，`Tag 9`，Requester `000:00.0`
- `Packet 2093075`，`Cpl`，`Tag 9`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 2093072`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 148,538 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 2093071` 和 `Packet 2093075` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F010`，group `G010`，candidates `C010`、`C028`。

## Finding F011

### 主要定位點

`Packet 1944539`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093079`

### 觀察到什麼

4.848 sec，`Packet 1944539` 的 `CfgRd0`（`Tag 15`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093079` 再次出現（5.880 sec，`MRd(32)`）。

5.880 sec，`Packet 2093079` 的 `MRd(32)` request（`Tag 15`）收到 `Packet 2093081` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 2093072`，`ERR_COR`（5.880 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944539`，`CfgRd0`，`Tag 15`，Requester `000:00.0`

#### Segment B（5.880 sec）

- `Packet 2093079`，`MRd(32)`，`Tag 15`，Requester `000:00.0`
- `Packet 2093081`，`Cpl`，`Tag 15`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 2093072`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 148,542 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 2093079` 和 `Packet 2093081` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F011`，group `G011`，candidates `C011`、`C029`。

## Finding F012

### 主要定位點

`Packet 1944547`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093091`

### 觀察到什麼

4.848 sec，`Packet 1944547` 的 `CfgRd0`（`Tag 4`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093091` 再次出現（5.880 sec，`MRd(32)`）。

5.880 sec，`Packet 2093091` 的 `MRd(32)` request（`Tag 4`）收到 `Packet 2093093` 的 Completion，status 是 `UR`。

附近也觀察到

- `Packet 2093072`，`ERR_COR`（5.880 sec）

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944547`，`CfgRd0`，`Tag 4`，Requester `000:00.0`

#### Segment B（5.880 sec）

- `Packet 2093091`，`MRd(32)`，`Tag 4`，Requester `000:00.0`
- `Packet 2093093`，`Cpl`，`Tag 4`，Requester `000:00.0`，Completer `001:00.0`，status `UR`
- `Packet 2093072`，`ERR_COR`，附近的 message

### 為什麼列出這一項

- 有 request 收到 status 為 `UR` 的 Completion，工具會列出 status 不是 `SC` 的 Completion。
- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。
- 這幾項觀察放在同一組，原因如下
  - 其中一項的 request 或 Completion 也是另一項的觀察位置
  - 它們用到同一個 packet
  - 它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- `ERR_COR` 和 `UR` 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。
- 這一組的 2 個 Segment 前後相隔約 148,546 packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。
- `Packet 2093091` 和 `Packet 2093093` 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F012`，group `G012`，candidates `C013`、`C031`。

## Finding F013

### 主要定位點

`Packet 1944549`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093522`

### 觀察到什麼

4.848 sec，`Packet 1944549` 的 `CfgRd0`（`Tag 10`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093522` 再次出現（5.883 sec，`CfgRd0`）。

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944549`，`CfgRd0`，`Tag 10`，Requester `000:00.0`

#### Segment B（5.883 sec）

- `Packet 2093522`，`CfgRd0`，`Tag 10`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- 同一組 `RequesterId` + `Tag` 的兩次出現相隔約 148,973 packets，key 相同不代表兩次出現屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F013`，group `G013`，candidates `C014`。

## Finding F014

### 主要定位點

`Packet 1944553`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093550`

### 觀察到什麼

4.848 sec，`Packet 1944553` 的 `CfgRd0`（`Tag 6`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093550` 再次出現（5.883 sec，`CfgRd0`）。

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944553`，`CfgRd0`，`Tag 6`，Requester `000:00.0`

#### Segment B（5.883 sec）

- `Packet 2093550`，`CfgRd0`，`Tag 6`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- 同一組 `RequesterId` + `Tag` 的兩次出現相隔約 148,997 packets，key 相同不代表兩次出現屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F014`，group `G014`，candidates `C016`。

## Finding F015

### 主要定位點

`Packet 1944555`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093564`

### 觀察到什麼

4.848 sec，`Packet 1944555` 的 `CfgRd0`（`Tag 12`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093564` 再次出現（5.883 sec，`CfgRd0`）。

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944555`，`CfgRd0`，`Tag 12`，Requester `000:00.0`

#### Segment B（5.883 sec）

- `Packet 2093564`，`CfgRd0`，`Tag 12`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- 同一組 `RequesterId` + `Tag` 的兩次出現相隔約 149,009 packets，key 相同不代表兩次出現屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F015`，group `G015`，candidates `C017`。

## Finding F016

### 主要定位點

`Packet 1944557`，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。

其他位置

- Segment B，`Packet 2093577`

### 觀察到什麼

4.848 sec，`Packet 1944557` 的 `CfgRd0`（`Tag 2`）送出後，還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 `Packet 2093577` 再次出現（5.883 sec，`CfgRd0`）。

### 相關位置

#### Segment A（4.848 sec）

- `Packet 1944557`，`CfgRd0`，`Tag 2`，Requester `000:00.0`

#### Segment B（5.883 sec）

- `Packet 2093577`，`CfgRd0`，`Tag 2`，Requester `000:00.0`

### 為什麼列出這一項

- 同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。

### 目前還不能確定

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。
- 同一組 `RequesterId` + `Tag` 的兩次出現相隔約 149,020 packets，key 相同不代表兩次出現屬於同一個故障事件。
- 同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。

### 追溯

`findings.json` 的 `F016`，group `G016`，candidates `C018`。

## 資料來源

- `findings.json` SHA-256 `B36283941560512B24A25C2DB6333AF9A8E4FE8FFFC76B9BAA35DCE581B02936`，本報告的所有觀察都來自這個檔案。
- Trace 檔名 `S0-Remove SD7-1350.pex`，由產生報告時的命令列提供。
- Trace SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB`，由命令列提供。
- TLP 總數 938，由命令列提供，來自已驗證的 G1a 計數。
