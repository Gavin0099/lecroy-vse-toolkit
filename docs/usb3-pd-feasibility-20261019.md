# USB3／PD 資料與原生定位可行性驗證

日期：2026-10-19。範圍為實際讀取既有 trace、核對欄位及 LeCroy 畫面；
本輪沒有把 USB3／PD 接入產品分析器，也沒有新增候選排序規則。

## 結論與實作影響

| 項目 | 本輪實測結果 | 對下一步的影響 |
| --- | --- | --- |
| USB3 Link Command | 現有 U02 runner 可重跑；取得原生 Packet 編號、秒／奈秒、channel、SS／SSP、command、Info／CRC5 及 replica 欄位 | 沿用現有擷取能力，補工具 adapter；不重寫 decoder |
| USB3 LFPS | 現有 U03 runner 可重跑；取得 Packet、時間、channel、類型、duration_ns、pattern 欄位 | 足以開始 Link／LFPS 的有界單檔導引；Wake 出現不等於 Wake 成功或故障 |
| USB3 LTSSM | 可計數並取得 callback 位置；原生畫面也可顯示狀態帶，但機器輸出仍沒有已核實的 state 名稱欄位 | 保留位置線索；精確狀態轉換分析暫不列入首版，不猜 `in.State` |
| PD 原生解析結果 | 五份官方範例均可由 Automation 匯出 Transaction／Transfer，包含協商、VDM、回應狀態及時間 | **PD 優先採用 Automation 的既有分組，VSE 僅補缺欄** |
| PD 封包共通欄位 | 沿用既有 U01 COM host，加小型研究 VSE，實際取得 Packet、時間、SOP／SpecRev／MsgID／DR／PR／Object Count 等 raw 欄位 | 可補原生 CSV 的封包定位與 header 證據；不是完整 payload／extended-message parser |
| 原生定位 | USB3 Packet 8、629253，以及 PD Packet 110、160、Transfer 6、8 的 trace／編號／時間已核對原生畫面 | 通路可沿用；工具需要支援有層級的定位目標，並處理原生顯示層級 |

本機實測版本為 **LeCroy USB Protocol Suite 10.40 Build 6309**。
官方 10.50 文件用於確認介面定義，沒有實機 10.50 執行證據。
資料與定位可行，不代表單檔候選品質、GL3525 PD 故障覆蓋或工程師省時已通過。

## 輸入與方法

建立十份來源的 SHA-256、大小、修改時間及屬性快照，實際開啟其中八份。
所有開啟都使用 repo 外的獨立唯讀副本；沒有 Save、錄製、硬體操作或 COM 註冊修改。
檔名僅用於辨識來源，不當成故障真值。

| 來源 | 本輪執行 | 證據範圍 |
| --- | --- | --- |
| 使用者 `dp1 hub detect SSD fail-2.usb`，SHA `f94e3e60d68f…` | Automation、既有 U02／U03、presence、原生導航 | USB3／SSP 與 LFPS 資料；不是獨立故障盲測 |
| 使用者 `dp1 hub detect SSD Ex power ok-4.usb`，SHA `0b2131b25441…` | presence | 確認所選事件及 PD 是否可見；不重新解讀檔名 PASS／FAIL |
| 官方 `SSP-Full LinkUp.usb`，SHA `08e3a3e3270d…` | Automation、presence | Link-up 類資料及空 Transaction／Transfer 匯出的行為 |
| 官方 `PD_Capabilities_Request.usb` | Automation、研究 VSE、原生導航 | 基本電力協商、VDM／DisplayPort 流程及定位 |
| 官方 `PD_CC_Adapter_PlugIn.usb` | Automation | CC 與 PD 原生分組資料 |
| 官方 `PD_Vendor_Defined.usb` | Automation、研究 VSE | VDM 欄位、命令與回應 |
| 官方 `PPS Power Negotiation.usb` | Automation、研究 VSE | PPS 類資料可取得；不是完整 PPS 規則資格化 |
| 官方 `PR_Swap_VDM.usb` | Automation | role swap／VDM 原生資料可匯出；不是 swap 時序驗收 |
| 官方 `PD_Eye_Example.usb`、`Power_Tracker_U1_U2_U3.usb` | 只盤點及 hash，未開啟 | 電氣／Eye 與額外電源狀態分析不在本輪執行範圍 |

官方範例位於 `C:\Users\Public\Documents\LeCroy\USB Protocol Suite\Examples`。
原始 trace、官方程式與完整匯出資料均未複製入 Git。

執行路徑：

- USB3 U02／U03 使用未修改的 `tools/usb_field_probe.py`、
  `tools/run-usb-field-probe.ps1` 及既有驗證流程，輸出 sample limit 32。
- Automation 使用同一個受控 COM 工作階段呼叫 `ExportToCsv` 的 0／1／3 層級，
  本輪有界範圍為 0～255；另匯出 Packet 0～12 的 native text。
- PD 研究 VSE 使用未修改的 `tools/u01-selection-host.cs`。小型腳本放在外部證據目錄，
  訪問選定事件並限制輸出前 64 筆 PD Packet、32 筆 PD Transfer；不新增產品規則。
- 共用現有 native mutex、PID／啟動時間／副本視窗身分及 STA message pump。
  開啟前無既有 UsbSuite；只關閉本輪擁有的工作階段，沒有強制終止使用者程序。

## USB3 可取得的欄位與缺口

U02 本次 visited／known／emitted／unknown／mismatch 為
`166196 / 166196 / 32 / 0 / 0`；U03 為 `47006 / 47006 / 32 / 0 / 0`。
這是所選事件的計數與前 32 筆欄位驗證，不是每筆 payload 或整份 trace 的協定驗證。

| 類別 | 實際可用 | 本輪仍未資格化 |
| --- | --- | --- |
| 共通識別 | Packet index、level、秒／奈秒、channel_raw、speed_raw、來源 hash | 混合 USB2／USB3／PD 檔案的 namespace 行為、完整捕獲起訖保證 |
| Link Command | vendor command name／raw、Info／CRC5、SSP replica Info／CRC5 | 每種 command 的故障含義、重試門檻與完整單檔異常判斷 |
| LFPS | vendor type／raw、duration_ns、pattern_type、starts_pattern | Wake／Reset 是否成功、量測解析度、未見後續時是否因 capture 截斷 |
| LTSSM | 事件計數、時間、channel、定位 anchor | 可機器讀取且有獨立核對的精確狀態名稱與轉換 |
| Transaction／Transfer | 使用者 USB3 trace 可匯出原生 group rows | group→完整 child Packet membership、所有 bulk／streams／status 語意 |

LTSSM callback 可與實際 LC／DP Packet 共用 index，甚至在不同 channel 重複出現。
例如第一筆 LTSSM anchor 與 Packet 8 的 Link Command 同時間、同 index。
不能把 callback index 當成獨立的 LTSSM 單位編號，也不能據此補寫狀態名稱。
舊 [U04／U05 欄位缺口](usb-field-probes-20261013.md) 因此仍保留原範圍。

官方 LinkUp 範例的 Packet CSV 有輸出；對本輪 1／3 層級範圍，API 返回後未產生 CSV。
研究 harness 將「沒有輸出檔」保留為 postcondition error。
這不能直接解讀成 API 不支援，也不能悄悄當成有完整結果的空表。

## PD 可取得的欄位與缺口

五份官方範例分別匯出 **9、10、8、3、15** 筆 PD Transfer，原生編號皆連續。
本輪已證明 LeCroy 有可直接重用的 PD 語意分組，無須先自行重建整個 PD state machine。

| 資料來源 | 實際觀察到的欄位／內容 | 使用限制 |
| --- | --- | --- |
| Automation Packet CSV | Packet 或 packet range、Type、timestamp、Additional Fields | 壓縮群組可能留空 Packet 欄，再寫 `13 Packets(110-122)`；不能一 row 當一 Packet |
| Automation Transaction CSV | PD Msg／Msg Type、DR／PR、Msg ID、Retry Cnt、Time／Time Stamp、PDO／RDO 顯示欄位、VDM Cmd／Cmd Type／Vendor ID | 欄名會因 trace 改變，有空白／重複欄名與帶單位字串；raw 與 decoded display 需分開 |
| Automation Transfer CSV | Power Negotiation、Cap Mismatch、Obj Pos、Selected Cap、Voltage／Max Cur；Discover Identity／SVIDs／Modes、Enter Mode、DP Status／Configure、ACKed／NAKed 等 Status | 某些 duration 留空；NAK、Mismatch、Retry 是觀察線索，不能單獨裁定裝置故障 |
| 最小 PD VSE | Index／Level、秒／奈秒、Channel、PacketType、SenderPort；SOP_Type、Spec_Rev、Msg_ID、DR、PR、Obj_Cnt、BufferLen；TransferType | 多數 header 先保留 raw，需對照已安裝版本常數；role 需依 SOP 情境判讀，不能直接套到 cable packet |
| VSE decoded lookup | Source Cap 的 Supply Type／Voltage／Max Cur；VDM Vendor ID／Cmd／Cmd Type | Request current 與 VDM version 的部分 decoded lookup 仍為空，不填 0，不宣稱完整 payload |

研究初版以未確認名稱查詢 VDM command，結果為空；查閱已安裝 vendor source 後，
將 `OBJ1_Command` 修正為 `OBJ1_Cmd`，新版實際得到 Discover Identity 等命令。
原版及新版證據都保留。`OBJ1_OprCurPow` 與 `OBJ1_VDM_Ver` 的 decoded lookup
仍未取得值；Automation 雖有相關顯示欄位，也不能據此宣稱 raw payload 已還原。

例如原生 RDO 顯示同時含電流／功率兩種單位，必須結合所選 PDO 類型解讀。
延伸訊息、多資料物件完整內容、raw payload bytes、CRC／NoGoodCRC／NoPS_RDY 等
錯誤旗標正例、Incomplete Transfer selection，均未在這輪完成資格化。

兩份既有使用者 USB3 trace 的 presence 結果為：

| Trace | SS／SSP 事件 | PD Packet | CC 事件 | LTSSM | LFPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fail-2` | 3,174,689 | 0 | 1 | 30 | 47,006 |
| `Ex power ok-4` | 5,147,883 | 0 | 1 | 35 | 1,175 |
| 官方 LinkUp | 1,250,138 | 0 | 0 | 20 | 344 |

**CC 事件不等於 PD 訊息。** 本輪 PD 資料可行性來自官方 PD capture，
尚無使用者 GL3525 故障 capture 的 CC-wire PD 流程證據，也沒有把主機 I²C
對 PD controller 的存取當成 PD 線上訊息。

## 原生定位的實際落點

| Trace／目標 | GotoUnit 層級 | 已核對原生畫面 | 定位路徑 |
| --- | ---: | --- | --- |
| USB3 fail-2 Packet 8 | 0 | `LGOOD_11`、Right、G2 x1、`0.000067664 s` | 現有 worker 的外部研究副本，只改成可指定 level |
| USB3 fail-2 Packet 629253 | 0 | LFPS `Handshake(U3 Wake)`、Left、`13.897383272 s`、顯示 `1.873 ms` | 同一工作階段，OpenFile 仍為 1 次；VSE 精確 duration 為 1,873,296 ns |
| PD Cap Packet 110 | 0 | `110-122` Source Cap 壓縮群組、`7.165679376 s`、Fixed 5.00 V／0.90 A | level-aware 研究 worker；只確認群組，不聲稱已展開每個 child |
| PD Cap Packet 160 | 0 | DP Configure／DisplayPort NAK、`7.760863328 s` | 同一工作階段，OpenFile 仍為 1 次 |
| PD Cap Transfer 6 | 3 | Enter Mode／DisplayPort ACKed、`7.752841390 s`、Obj Pos 1 | **未修改的現有產品 worker**；首次到 Packet 150 起點，手動按 XFR 後核對 Transfer 6 |
| PD Cap Transfer 8 | 3 | DP Configure／DisplayPort NAKed、`7.759134390 s` | 同一未修改 worker，OpenFile 仍為 1 次 |

`GotoUnit(level,index)` 可以使用 PD 原生 Transfer namespace。
但 **API 的定位層級與 GUI 當前顯示層級是兩件事**；本輪曾手動切換 XFR，
沒有證明產品會自動選對顯示層級。USB3 的 Packet 定位使用研究副本，尚未加入產品。

保留的暖呼叫 API 時間：PD Packet 160 為 36 ms，PD Transfer 8 為 31 ms，
USB3 Packet 629253 為 24 ms；首次開檔約 7.3～11.8 秒。
這些是個別呼叫時間，不含人工切換顯示、閱讀與核對，不是工程師任務耗時。
worker 的 `gui_confirmed=false` 仍忠實保留；GUI 證據另由畫面檢查紀錄提供。

## 驗證與證據

本輪外部證據根目錄為：

`C:\Users\reiko\.codex\visualizations\2026\10\16\01a14297-966e-7b51-b3e6-572fecb51b9e\usb3-pd-feasibility-20261019`

- [驗證結果與來源完整性](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/usb3-pd-feasibility-20261019/verification.json>)
- [可重跑的唯讀檢查](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/usb3-pd-feasibility-20261019/verify.py>)
- [六個原生畫面觀察及截圖索引](<C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/usb3-pd-feasibility-20261019/gui-observations.json>)

`verify.py` 對十份原始檔重新核對 hash／大小／修改時間／屬性，並檢查 15 次研究 probe
的來源／唯讀副本與 native 完成狀態、兩次既有 U02／U03 runner 結果、PD 原生欄位、
五筆另存的 API 回應、三個導航工作階段關閉及 tracked source 保留。
Packet 110 首次回應沒有另存而被下一次請求覆寫，故不計入五筆持久化 API assertion；
其 GUI 畫面與觀察紀錄仍保存。未以文件修改為由重跑不相關的產品測試。

本機證據連結依賴這台機器，並非可攜式測試包；來源完整 SHA 與所有研究腳本保存於該目錄。
後續若要讓其他工程師重現，應另準備可授權分享的 trace／去識別匯出及版本環境。

官方定義參考：
[Automation Trace API](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/primary-dual-interface-for-trace)
定義 Packet／Transaction／Transfer 的 0／1／3 層級與匯出介面；
[VSE Input Context](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/input-context-members)
及 [Engine Events](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/engine-events)
提供欄位及事件語意。文件能力與本輪 runtime 實測範圍分開看待。

後續實作順序與驗收見 [USB3／PD Tool Plan](usb3-pd-tool-plan.md)。
