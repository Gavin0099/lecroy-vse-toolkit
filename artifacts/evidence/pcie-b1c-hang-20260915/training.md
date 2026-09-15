# PCIe Link Training 流程（B1c）

來源 `timeline.json` SHA-256 `D612F674B9F10A620D98AFE1A7823F8C852EC5BEB9254C5E7841628A89C7FF41`，packet 範圍 225041 至 1484414。本文件只整理 B1b 擷取到的事件，沒有套用任何 link 判斷規則。

相鄰 segment 的顯示時間相差 0.1 sec 以上時，列為「沒有觀察到事件」。這是呈現用的門檻，不是 PCIe 規則；時間解析度是 PETracer 顯示值。

## 流程總覽

Detect（Upstream） → Recovery（Downstream） → link condition ×9 → Recovery（Downstream） → link condition ×1 → Recovery（Downstream） → Polling（Downstream） → 沒有觀察到事件（1.312 sec） → link condition ×1 → Polling（Upstream） → Configuration（Downstream、Upstream） → Recovery（Downstream、Upstream） → L0（Downstream、Upstream）

## 尚未確認

- `HasErrors` 有計數，但 B1b 讀取的 13 個子旗標全部為 0，error subtype 為 `UNKNOWN`。
- 各階段的 TS1、TS2、DLLP 等計數沒有按方向拆開；方向只來自階段起點的 LTSSM 或 link condition 紀錄，未逐事件證明。
- `LINK_UP` / `LINK_DOWN` 使用 VSE 常數名稱，文字意義尚未在 PETracer GUI 核對。
- speed code 的 GT/s 標示來自 VSE 手冊文字，未經 probe 驗證。

## 階段 1：Detect

- 範圍：Packet 225041 至 225050，9.512 sec 至 9.512 sec，segment 1 至 1。
- link condition `LINK_DOWN`，Upstream，Packet 225041，9.512 sec
- LTSSM Detect，Upstream，Packet 225041，9.512 sec（analyzer 標示 state not valid）
- 事件 10：TLP 2、NAK DLLP 1、FC DLLP 6
- `HasErrors` 0
- NAK DLLP seq 1682，Downstream，Packet 225042
- TLP `CfgRd0`，Downstream，Packet 225043
- TLP `CfgRd0`，Downstream，Packet 225048

## 階段 2：Recovery

- 範圍：Packet 225051 至 990789，9.512 sec 至 9.538 sec，segment 2 至 3。
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 225051，9.512 sec
- link condition `LINK_DOWN`，Downstream，Packet 990789，9.538 sec
- LTSSM Recovery.RCVRSPD，Downstream，Packet 990789，9.538 sec
- 事件 765,738：TS1 742,531、EIOS 1、EIEOS 23,205
- `HasErrors` 0

## 階段 3：link condition 變化

- 範圍：Packet 990790 至 990798，9.538 sec 至 9.552 sec，segment 4 至 12。
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
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 990799，9.552 sec
- link condition `LINK_DOWN`，Downstream，Packet 1096915，9.563 sec
- LTSSM Recovery.RCVRSPD，Downstream，Packet 1096915，9.563 sec
- 事件 106,117：TS1 106,116
- `HasErrors` 1，error subtype：`UNKNOWN`
- speed code 0（手冊標示 2.5 GT/s），width x1，Downstream，Packet 990799

## 階段 5：link condition 變化

- 範圍：Packet 1096916 至 1096916，9.575 sec 至 9.575 sec，segment 15 至 15。
- link condition `LINK_UP`，Downstream，Packet 1096916，9.575 sec
- 事件 1
- `HasErrors` 0

## 階段 6：Recovery

- 範圍：Packet 1096917 至 1096917，9.575 sec 至 9.575 sec，segment 16 至 16。
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 1096917，9.575 sec
- 事件 1：TS1 1
- `HasErrors` 1，error subtype：`UNKNOWN`

## 階段 7：Polling

- 範圍：Packet 1096918 至 1479759，9.575 sec 至 9.600 sec，segment 17 至 17。
- LTSSM Polling，Downstream，Packet 1096918，9.575 sec（analyzer 標示 state not valid）
- 事件 382,842：TS1 382,842
- `HasErrors` 382,842，error subtype：`UNKNOWN`

## 階段 8：沒有觀察到事件

- 從 9.600 sec（Packet 1479759）到 10.912 sec（Packet 1479760），相差 1.312 sec。
- 範圍內沒有 TLP、DLLP、ordered set、link condition 或 EIE 事件送達 script；EIE 在整份 trace 都沒有送達，electrical idle 無法用這個方式觀察。

## 階段 9：link condition 變化

- 範圍：Packet 1479760 至 1479844，10.912 sec 至 10.912 sec，segment 18 至 18。
- link condition `LINK_UP`，Upstream，Packet 1479760，10.912 sec
- 事件 85：TS1 84
- `HasErrors` 84，error subtype：`UNKNOWN`

## 階段 10：Polling

- 範圍：Packet 1479845 至 1484024，10.912 sec 至 10.912 sec，segment 19 至 19。
- LTSSM Polling，Upstream，Packet 1479845，10.912 sec
- 事件 4,180：TS1 2,984、TS2 1,196
- `HasErrors` 2,065，error subtype：`UNKNOWN`
- speed code 0（手冊標示 2.5 GT/s），width x1，Upstream，Packet 1479845

## 階段 11：Configuration

- 範圍：Packet 1484025 至 1484185，10.912 sec 至 10.912 sec，segment 20 至 27。
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
- LTSSM Recovery.RCVRLOCK，Downstream，Packet 1484186，10.912 sec
- LTSSM Recovery.RCVRLOCK，Upstream，Packet 1484200，10.912 sec
- LTSSM Recovery.RCVRCFG，Upstream，Packet 1484216，10.912 sec
- LTSSM Recovery.RCVRCFG，Downstream，Packet 1484229，10.912 sec
- 事件 87：TS1 36、TS2 51
- `HasErrors` 0

## 階段 13：L0

- 範圍：Packet 1484273 至 1484414，10.912 sec 至 10.912 sec，segment 32 至 33。
- LTSSM L0，Downstream，Packet 1484273，10.912 sec
- LTSSM L0，Upstream，Packet 1484298，10.912 sec
- 事件 142：TLP 2、FC DLLP 99、other DLLP 41
- `HasErrors` 0
- TLP `Msg`，Upstream，Packet 1484399
- TLP `MsgD`，Downstream，Packet 1484414
