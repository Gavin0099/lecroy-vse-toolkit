# USB U02 / U03 native field checkpoints

最新授權允許逐片實作、驗證、review 後續作，不逐片重新詢問。以下為當前同一 SHA-256 USB trace 的局部實證；不擴大原 DEMO PASS、W1–W5 或 protocol correctness 範圍。

工程師現在可以查到「哪個 packet 的 native link-command 名稱／兩組 word 欄位」及「哪個 LFPS record 的 raw type／pattern／duration 與 vendor 名稱」，每列有 trace hash、packet index、level、channel 及原始時間。Whole capture 的 mode、epoch、完整性和量測準確度仍未知。

## U02 — LINK_CMD

[Review](../artifacts/evidence/serial-slices-20261013/u02-review.json) 通過 SSP 樣本範圍：166,196 個 callback 的前 128 列，兩次輸出一致，含 LGOOD_0–15 與 LCRD1_A–D。LBAD／LRTY／LGO、SS mode 與其他未取樣類型沒有資格化。

LC-04 PDF32 的兩組 `LinkCmdInfo`／CRC5 實際可讀。USB-01 Revision1.1 §7.2.2.1–2／§7.3.5 與 Figure7-13 明確包含 word replica；沒有把第二組在 SS／SSP 任一模式中自行標成不適用。Info 為 11 bits、CRC 為 5 bits。

另以 `GetPacket` 讀回兩份 64-bit 原始表示，依 Figure7-13 的 byte0／LSB-first 及 Table7-3 的 word 位置，對照 VSE 欄位：

| Native packet | Word／replica raw bytes | Info／CRC5／replica info／CRC5 |
| --- | --- | --- |
| 8，LGOOD_11 | `0B 20 0B 20` | `11 / 4 / 11 / 4` |
| 9，LCRD1_A | `80 A0 80 A0` | `128 / 20 / 128 / 20` |

這是兩個代表性 packet 的欄位位元核對，沒有運算 CRC polynomial 或判定 command 合法性。`lnkcmd_raw` 是 LeCroy enum，例如 LGOOD_11 為 27；wire information 為 11，兩者不混用。Raw source：[raw.json](../artifacts/evidence/serial-slices-20261013/u02-raw-packets/raw.json)。

## U03 — LFPS

[Review](../artifacts/evidence/serial-slices-20261013/u03-review.json) 通過 raw＋vendor-name 樣本範圍：47,006 個 callback 的前 128 列，兩次输出一致。128 列的 Type、duration 三欄、PatternType、StartsPattern 全部對上已資格化同 trace 的歷史保存 raw 資料；歷史檔只讀、未改写。

目前樣本含 `LFPS_ILLEGAL`、`LFPS_POLLING`、`LFPS_RESET`、`LFPS_WAKE_U3`，名稱直接來自安裝版 `GetLfpsDesc`；不由 duration 猜 type。Native name 與歷史 raw 共用 LeCroy decoder，不能當獨立 electrical oracle。Wake／reset 成功、pattern end、capture 截斷與量測準確度未判定。Row 的 SS／SSP 是該 event 的 native Speed context，不是整份 capture 的 negotiated mode。

## 程式與測試

- [Field preparer／validator／S01 sidecar](../tools/usb_field_probe.py)
- [唯讀 runner](../tools/run-usb-field-probe.ps1)，使用已修正的 USB host
- [Fixtures tests](../tests/usb_fields/test_usb_field_probe.py)／[獨立預期依據](../tests/usb_fields/fixture-oracles.md)

輸出包括 plan/script SHA、source／copy 前後身分、toolchain hashes、raw reports、typed observations 與 S01 manifest。Manifest 保留 capture mode／epoch／起訖及 retention unknown；field availability 只表示這份輸出能取得，沒有 compliance verdict。兩個 protocols 的 extraction／scoring 既有 pipeline 未重構。

## 後續 gate

U04 以三個已保存 LTSSM callback 的精確 index 做唯讀 native export；輸出是相同時間的 LC／DP packet，未給可確認的 state 欄名。[Discovery](../artifacts/evidence/serial-slices-20261013/u04-discovery/discovery.json) 保存 source bindings；state adapter 為 `blocked_field`，不猜 `in.State` 或 generic field label。

U05 成功匯出三個 transaction／transfer native units，確認 group namespace 及 G2 資料。[Discovery](../artifacts/evidence/serial-slices-20261013/u05-discovery/discovery.json) 的 CSV 未提供明確子 packet references；manual 的 `FirstInXfer`／`LastInXfer` 是 transaction 的位置旗標，也不能代替 packet list。故完整 grouping qualification 保留 HOLD，不假設 group index 是 packet number。相關 U07／U09 不能在缺 refs／payload／status 資格化時跳過依賴。

U04／U05 的缺口不改成其他分支失敗；後續已接 PCIe P01 selection probe。其他片仍須自己的資料、正文及工程師定義門檻。
