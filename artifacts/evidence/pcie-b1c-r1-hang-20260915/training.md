# PCIe Link Training 流程（B1c-r1）

來源 `timeline.json` SHA-256 `D612F674B9F10A620D98AFE1A7823F8C852EC5BEB9254C5E7841628A89C7FF41`，packet 範圍 225041 至 1484414。本文件只整理 B1b 擷取到的事件，沒有套用任何 link 判斷規則。

相鄰 segment 的顯示時間相差 0.1 sec 以上時，列為「沒有觀察到事件」。這是呈現用的門檻，不是 PCIe 規則；時間解析度是 PETracer 顯示值。

方向與 GUI 抽樣來自 B1c-x2 `haserrors.json` SHA-256 `84BF5F768D986558E942CAF36E685C2B7D0589A2E319D993C972196248F6B9BF` 與 GUI 觀察 `gui-observations.json` SHA-256 `1D6A2D7448AF00E69B87F7DE7D9403E6658AE743D573CC6A4D0290F2F9049566`。每個階段列出進入時各方向最後一筆 LTSSM 紀錄；`HasErrors` 的方向只在所屬範圍內全部落在同一方向時標示。

## 流程總覽

Detect（起點 Upstream） → Recovery（起點 Downstream） → link condition ×9（起點 Downstream） → Recovery（起點 Downstream） → link condition ×1（起點 Downstream） → Recovery（起點 Downstream） → Polling（起點 Downstream） → 沒有觀察到事件（1.312 sec） → link condition ×1（起點 Upstream；HasErrors 在 Downstream，Downstream 仍為 Polling） → Polling（起點 Upstream；HasErrors 在 Downstream，Downstream 仍為 Polling） → Configuration（起點 Downstream、Upstream） → Recovery（起點 Downstream、Upstream） → L0（起點 Downstream、Upstream）

## 已核對

- Packet 225041 在 PETracer GUI 顯示 Link Event「Link Down」，與 `LINK_DOWN` 一致（B1c-x1）。
- Packet 1479760 在 PETracer GUI 顯示 Link Event「Link Up」，與 `LINK_UP` 一致（B1c-x1）。

## 範圍層級方向統計（B1c-x2）

| 範圍 | Packet | Channel | 事件 | TS1 | `HasErrors` |
| --- | --- | --- | --- | --- | --- |
| R1 | 225041 至 1096917 | _CHANNEL_1 | 1 | 0 | 0 |
| R1 | 225041 至 1096917 | Downstream | 871,875 | 848,648 | 2 |
| R2 | 1096918 至 1479759 | Downstream | 382,842 | 382,842 | 382,842 |
| R3 | 1479760 至 1484414 | _CHANNEL_1 | 2,288 | 994 | 0 |
| R3 | 1479760 至 1484414 | Downstream | 2,367 | 2,207 | 2,149 |

## 尚未確認

- `HasErrors` 在 GUI 抽樣中對應 analyzer 的 Training Sequence Error，但只看了 3 筆；各階段 `HasErrors` 的子類型分布為 `UNKNOWN`。
- 單一階段內的 TS1、TS2、DLLP 等計數沒有按方向拆開；方向拆分只到 B1c-x2 的 R1、R2、R3 範圍層級。
- speed code 的 GT/s 標示來自 VSE 手冊文字，未經 probe 驗證。
- B1c-x2 樣本沒有出現 `_CHANNEL_1` 的名稱，範圍統計以 channel id 列出。

## 階段 1：Detect

- 範圍：Packet 225041 至 225050，9.512 sec 至 9.512 sec，segment 1 至 1。
- 進入此階段時各方向最後 LTSSM：尚無紀錄
- link condition `LINK_DOWN`，Upstream，Packet 225041，9.512 sec
- LTSSM Detect，Upstream，Packet 225041，9.512 sec（analyzer 標示 state not valid）
- 事件 10：TLP 2、NAK DLLP 1、FC DLLP 6
- `HasErrors` 0
- NAK DLLP seq 1682，Downstream，Packet 225042
- TLP `CfgRd0`，Downstream，Packet 225043
- TLP `CfgRd0`，Downstream，Packet 225048

## 階段 2：Recovery

- 範圍：Packet 225051 至 990789，9.512 sec 至 9.538 sec，segment 2 至 3。
- 進入此階段時各方向最後 LTSSM：Upstream Detect（Packet 225041，state not valid）
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 225051，9.512 sec
- link condition `LINK_DOWN`，Downstream，Packet 990789，9.538 sec
- LTSSM Recovery.RCVRSPD，Downstream，Packet 990789，9.538 sec
- 事件 765,738：TS1 742,531、EIOS 1、EIEOS 23,205
- `HasErrors` 0

## 階段 3：link condition 變化

- 範圍：Packet 990790 至 990798，9.538 sec 至 9.552 sec，segment 4 至 12。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRSPD（Packet 990789）、Upstream Detect（Packet 225041，state not valid）
- link condition `LINK_UP`，Downstream，Packet 990790，9.538 sec
- link condition `LINK_DOWN`，Downstream，Packet 990791，9.541 sec
- link condition `LINK_UP`，Downstream，Packet 990792，9.541 sec
- link condition `LINK_DOWN`，Downstream，Packet 990793，9.545 sec
- link condition `LINK_UP`，Downstream，Packet 990794，9.545 sec
- link condition `LINK_DOWN`，Downstream，Packet 990795，9.548 sec
- link condition `LINK_UP`，Downstream，Packet 990796，9.548 sec
- link condition `LINK_DOWN`，Downstream，Packet 990797，9.552 sec
- link condition `LINK_UP`，Downstream，Packet 990798，9.552 sec
- 事件 9
- `HasErrors` 0

## 階段 4：Recovery

- 範圍：Packet 990799 至 1096915，9.552 sec 至 9.563 sec，segment 13 至 14。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRSPD（Packet 990789）、Upstream Detect（Packet 225041，state not valid）
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 990799，9.552 sec
- link condition `LINK_DOWN`，Downstream，Packet 1096915，9.563 sec
- LTSSM Recovery.RCVRSPD，Downstream，Packet 1096915，9.563 sec
- 事件 106,117：TS1 106,116
- `HasErrors` 1，error subtype：`UNKNOWN`；方向 Downstream（依據 B1c-x2 R1：Packet 225041 至 1096917 的 2 筆 `HasErrors` 全部在 Downstream）
- GUI 抽樣 Packet 990799（R→，2.5 GT/s x1）顯示 Training Sequence Error `TSDataRateErr`、`TSRsrvErr`、`TSLaneErr`、`TSTrainingControlErr`，僅代表此 sample。
- speed code 0（手冊標示 2.5 GT/s），width x1，Downstream，Packet 990799

## 階段 5：link condition 變化

- 範圍：Packet 1096916 至 1096916，9.575 sec 至 9.575 sec，segment 15 至 15。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRSPD（Packet 1096915）、Upstream Detect（Packet 225041，state not valid）
- link condition `LINK_UP`，Downstream，Packet 1096916，9.575 sec
- 事件 1
- `HasErrors` 0

## 階段 6：Recovery

- 範圍：Packet 1096917 至 1096917，9.575 sec 至 9.575 sec，segment 16 至 16。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRSPD（Packet 1096915）、Upstream Detect（Packet 225041，state not valid）
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 1096917，9.575 sec
- 事件 1：TS1 1
- `HasErrors` 1，error subtype：`UNKNOWN`；方向 Downstream（依據 B1c-x2 R1：Packet 225041 至 1096917 的 2 筆 `HasErrors` 全部在 Downstream）

## 階段 7：Polling

- 範圍：Packet 1096918 至 1479759，9.575 sec 至 9.600 sec，segment 17 至 17。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRLOCK（Packet 1096917）、Upstream Detect（Packet 225041，state not valid）
- LTSSM Polling，Downstream，Packet 1096918，9.575 sec（analyzer 標示 state not valid）
- 事件 382,842：TS1 382,842
- `HasErrors` 382,842，error subtype：`UNKNOWN`；方向 Downstream（依據 B1c-x2 R2：Packet 1096918 至 1479759 的 382,842 筆 `HasErrors` 全部在 Downstream）
- GUI 抽樣 Packet 1096918（R→，2.5 GT/s x1）顯示 Training Sequence Error `TSRsrvErr`，僅代表此 sample。

## 階段 8：沒有觀察到事件

- 從 9.600 sec（Packet 1479759）到 10.912 sec（Packet 1479760），相差 1.312 sec。
- 範圍內沒有 TLP、DLLP、ordered set、link condition 或 EIE 事件送達 script；EIE 在整份 trace 都沒有送達，electrical idle 無法用這個方式觀察。

## 階段 9：link condition 變化

- 範圍：Packet 1479760 至 1479844，10.912 sec 至 10.912 sec，segment 18 至 18。
- 進入此階段時各方向最後 LTSSM：Downstream Polling（Packet 1096918，state not valid）、Upstream Detect（Packet 225041，state not valid）
- link condition `LINK_UP`，Upstream，Packet 1479760，10.912 sec
- 事件 85：TS1 84
- `HasErrors` 84，error subtype：`UNKNOWN`；方向 Downstream（依據 B1c-x2 R3：Packet 1479760 至 1484414 的 2,149 筆 `HasErrors` 全部在 Downstream）
- GUI 抽樣 Packet 1479761（R→，2.5 GT/s x1）顯示 Training Sequence Error `TSRsrvErr`，僅代表此 sample。

## 階段 10：Polling

- 範圍：Packet 1479845 至 1484024，10.912 sec 至 10.912 sec，segment 19 至 19。
- 進入此階段時各方向最後 LTSSM：Downstream Polling（Packet 1096918，state not valid）、Upstream Detect（Packet 225041，state not valid）
- LTSSM Polling，Upstream，Packet 1479845，10.912 sec
- 事件 4,180：TS1 2,984、TS2 1,196
- `HasErrors` 2,065，error subtype：`UNKNOWN`；方向 Downstream（依據 B1c-x2 R3：Packet 1479760 至 1484414 的 2,149 筆 `HasErrors` 全部在 Downstream）
- speed code 0（手冊標示 2.5 GT/s），width x1，Upstream，Packet 1479845

## 階段 11：Configuration

- 範圍：Packet 1484025 至 1484185，10.912 sec 至 10.912 sec，segment 20 至 27。
- 進入此階段時各方向最後 LTSSM：Downstream Polling（Packet 1096918，state not valid）、Upstream Polling（Packet 1479845）
- LTSSM Configuration.LINKWIDTH_STRT，Downstream，Packet 1484025，10.912 sec
- LTSSM Configuration.LINKWIDTH_STRT，Upstream，Packet 1484046，10.912 sec
- LTSSM Configuration.LINKWIDTH_ACPT，Upstream，Packet 1484050，10.912 sec
- LTSSM Configuration.LINKWIDTH_ACPT，Downstream，Packet 1484053，10.912 sec
- LTSSM Configuration.LANENUM_WAIT_ACPT，Downstream，Packet 1484072，10.912 sec
- LTSSM Configuration.LANENUM_WAIT_ACPT，Upstream，Packet 1484097，10.912 sec
- LTSSM Configuration.COMPLETE，Downstream，Packet 1484118，10.912 sec
- LTSSM Configuration.COMPLETE，Upstream，Packet 1484147，10.912 sec
- 事件 161：TS1 97、TS2 64
- `HasErrors` 0

## 階段 12：Recovery

- 範圍：Packet 1484186 至 1484272，10.912 sec 至 10.912 sec，segment 28 至 31。
- 進入此階段時各方向最後 LTSSM：Downstream Configuration.COMPLETE（Packet 1484118）、Upstream Configuration.COMPLETE（Packet 1484147）
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 1484186，10.912 sec
- LTSSM Recovery.RCVRLOCK，Upstream，Packet 1484200，10.912 sec
- LTSSM Recovery.RCVRCFG，Upstream，Packet 1484216，10.912 sec
- LTSSM Recovery.RCVRCFG，Downstream，Packet 1484229，10.912 sec
- 事件 87：TS1 36、TS2 51
- `HasErrors` 0

## 階段 13：L0

- 範圍：Packet 1484273 至 1484414，10.912 sec 至 10.912 sec，segment 32 至 33。
- 進入此階段時各方向最後 LTSSM：Downstream Recovery.RCVRCFG（Packet 1484229）、Upstream Recovery.RCVRCFG（Packet 1484216）
- LTSSM L0，Downstream，Packet 1484273，10.912 sec
- LTSSM L0，Upstream，Packet 1484298，10.912 sec
- 事件 142：TLP 2、FC DLLP 99、other DLLP 41
- `HasErrors` 0
- TLP `Msg`，Upstream，Packet 1484399
- TLP `MsgD`，Downstream，Packet 1484414
