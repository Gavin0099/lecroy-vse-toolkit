# USB3／PD 測試的獨立依據

日期：2026-10-19。本文件說明 fixture／預期值從何而來，不把合成序列當硬體或盲測證據。

## 識別與資料欄位

- `navigation-contract.cs` 與 `test_expansion.py`：依
  [LeCroy GotoUnit 定義](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/primary-dual-interface-for-trace)，
  0／1／3 分別為 Packet／Transaction／Transfer；實作計畫另限制 USB3 首版只有 Packet、
  USB2 只有 Transfer。相同 index 不得跨 protocol／level 共用授權，過期 case／錯 hash 不可定位。
- `test_usb3_data.py`：Packet 8／`LGOOD_11`／67,664 ns／Info 11／CRC5 4，
  與 Packet 629253／`LFPS_WAKE_U3`／13,897,383,272 ns／duration 1,873,296 ns，
  均來自先前 U02／U03 的已核對輸出與原生畫面。來源 SHA-256
  `f94e3e60d68f08a90104b3d11ece6a89f0e34649bcfb5f0c616dd4f765d8540f`。
  新合併擷取另逐欄比較兩組前 32 筆，未拿自己的 parser 結果產生 expected 值。
- `test_pd_data.py`：官方 Capabilities 範例 SHA-256
  `48c1cb15ee7564ee8830b396bb61520e79ce4cc26d8f1ac5f102c8afadf89000`，
  Packet 110 在 7.165679376 s、SOP、Source Cap；Packet 160 在 7.760863328 s、
  DP Configure NAK；Transfer 8 在 7.759134390 s，CSV duration 留空。
  SOP／revision／MsgID／object-count 的欄位與數值空間依
  [官方 Input Context](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/input-context-members)。
  cable SOP 不自動套用一般 Port role；raw 欄位與原生顯示仍保留。
- CSV 重複欄名的測例是刻意建立的歧義輸入，不複製整份 vendor CSV。
  5 V 與 9 V 不能最後一欄蓋掉前欄；空白 duration 必須未知；改變已雜湊的檔案必須拒絕。
  API 返回卻沒有檔案、無唯一 Packet anchor 及缺結束標記，均有失敗／部分缺漏測例。

## 分析與介面政策

`test_usb3_guidance.py` 的 expected 值是以下經明確定義的產品政策，並非 USB 合規裁決：

1. 一個 Wake、Reset、Polling 或非法解碼不能單獨成為候選。
2. 可見 Link 流量後，同 channel 的 Reset／非法 LFPS 加 Polling，或 Wake 後 Reset、
   重複 Reset，可形成調查線索；若後面已有 LGOOD／LCRD 就不列為這類未恢復尾端候選。
3. 這只表示 Link Command 的可見性，不證明 Link 功能、裝置狀態、韌體根因或 timeout。
   不跨 channel 合併，不使用失敗時間、檔名或 PASS baseline。
4. 來源範圍未知需保留缺口；輸出截斷或選定事件速度未知時，不以缺少後續事件產生候選。

候選 card 必須有位置、事實、推薦理由、具體下一步和證據缺口。原生顯示層級提示與
`gui_confirmed=false` 保留，API 返回不等於已看到正確畫面。

`test_pipeline.py` 檢查實際保存的模型／報告／完整性紀錄及唯一唯讀副本；原生部分採
已定義的輸出 fixture 注入，與另外執行的 LeCroy 真實擷取／導航證據分開。
`workspace-contract.cs` 的預設協定順序來自計畫及實際 UX 缺陷：候選優先；無候選時
先顯示 failed／partial，再顯示有中性流程的協定、其他已分析協定，
避免資料警告或可閱讀 PD 流程被空頁遮住。單一速度計數不能替代 Link／LFPS 事件。

完整 native trace、vendor source、原始匯出與畫面留在 Git 外；fixture 測試通過不代表
10.50、混合協定 capture、陌生案例可靠度、真人操作或工程師省時通過。
## PD 導引補充

`test_pd_guidance.py` 的序列由人工結構政策建立，不是複製 analyzer 的輸出：
Request→Accept→Request 可作調查線索；Request→Accept→PS Ready、單次 Reject／Wait、
capture 尾端 Request→Accept 均不提升為候選。使用原生 Transaction，避免重複計算
wire retry。VDM 以同 SOP／channel／sender／vendor／command 的不同原生 Transfer
聚合重複 NAK／BUSY；後續 ACK、Reset／其他協商 epoch 分開。這是調查優先政策，
不是 PD 合規條文；沒有任意 timeout、根因或違規斷言。

官方 Cap 範例的單次 DP Configure NAK 不是故障 oracle。它應保留為中性流程，
Transfer6→Packet150（Enter Mode）及 Transfer8→Packet158／160（Configure REQ／NAK）
是已核對的定位／欄位 oracle。電壓 5.00 V／電流 0.90 A 為原生字串，
RDO 並列 A／W 不自行換算。真實 GL3525 PD 故障及獨立盲測仍待驗證。
