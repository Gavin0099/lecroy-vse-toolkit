# USB3／PD 擴充實作結果

2026-10-19。依使用者授權，按 EXP-01 → U3-01／02／03 → PD-01／02／03 →
EXP-02 執行。這是本機工程結果；外部資料、10.50 與真人驗收獨立列為待驗證。
目前沒有建立提交、push、PR 或 merge。

## 工程師現在可以做什麼

匯入一份 `.usb`，在原生工作區查看 USB2 EP0、USB3 Link／LFPS、PD 基本協商／VDM
各自的分析狀態與優先候選。每個候選有位置、現象、理由、下一步及證據缺口。
各協定獨立排序、最多三個；不使用 PASS baseline、FAIL 檔名或人工失敗時間。

PD 的正常協商及單次 NAK 另外列為「已觀察流程（非候選）」，可閱讀並回到原生工具，
不會為了提供導航而硬湊故障。自有分析保留在各 adapter；共用的只是工作生命週期、
展示、來源保護及有 protocol／level／index 的定位目標。

## 分片證據

| 分片 | 本機結果與可核對行為 | 尚未證明 |
| --- | --- | --- |
| EXP-01 | USB2 Transfer1386／562／372／446、USB3 Packet8／629253、PD Transfer6／8／Packet160 均實際核對；同工作階段 OpenFile=1；錯 protocol／level／hash／過期項目拒絕 | 自動切原生顯示層級、多實例隔離共存 |
| U3-01 | 兩份使用者 USB3、LinkUp、USB2-only 重跑；原 U02／U03 前32筆共64筆逐欄相符；全程計數與保存上限分開 | 精確 LTSSM state、完整 capture 邊界／child grouping |
| U3-02 | 結構正例、正常 Wake／單一警告、恢復、channel 分離、截斷與時間平移測例；開發 trace 得到兩個候選 | 陌生 trace 排名可靠度、根因 |
| U3-03 | 實際檔案選擇→同副本依序分析→原生候選／上下文→Packet3081311 時間／channel 核對；換檔會清理自有導航；無候選／部分資料畫面已檢查 | 新版真人操作效率 |
| PD-01 | 五份官方範例的 Transfer9／10／8／3／15 與原生 CSV 一致，所有起始群組都有唯一 Packet anchor；保留重複欄名、原生單位、空 duration | 真實 GL3525 PD 故障、完整 payload／error flags |
| PD-02 | Request→Accept→Request、重複 VDM NAK／BUSY 的保守聚合；正常完成、單次拒絕、wire retry、恢復、SOP／sender／Reset／資料缺漏反例；五份範例無強制候選 | PD 合規、計時、PPS／EPR／role swap／extended 規則 |
| PD-03 | 真實匯入 Cap 範例，9個中性流程；5.00V／0.90A、SOP／DR／PR 可讀，無假 Address／EP；工作區按鈕→Transfer8／6、Packet160 及 Transfer6 起點 Packet150 畫面核對，OpenFile=1 | 外部版本／真人資格化 |
| EXP-02 | 統一可攜包與本機整合／回歸；最終紀錄見本文下方驗證 | 真實混合 capture、獨立 USB3、GL3525 PD 故障、10.50、新機器、真人時間與錯誤方向 |

## 來源與候選結果

| 輸入 | 可見／保存資料 | 本版結果 |
| --- | --- | --- |
| 使用者 fail-2 | 3174690個 Packet事件；166196 Link Command、47006 LFPS、30 LTSSM anchors | 2個候選，Packet3081311／21.685629136s／channel5，Packet3081858／21.786751640s／channel6 |
| 使用者 Ex power ok-4 | 5147884個事件；353289 Link Command、1175 LFPS、35 LTSSM anchors；Link＋LFPS 保存達300000 | 明確 partial；未以後續缺失規則產生候選，不能視為 PASS |
| SSP-Full LinkUp | 2941 Link Command、344 LFPS、20 LTSSM anchors | 本範圍0候選 |
| USB2 PASS04 | 620103個 Packet事件，無本範圍 USB3 事件；CC1、PD0 | USB3／PD 未觀察到，不能推成整份 USB PASS |
| PD Cap／CC／VDM／PPS／Swap | PD Packet52／81／49／16／114，Transaction20／36／20／8／52 | 本範圍0候選，中性流程9／10／8／2／14；未識別的 native transfer仍在 raw，未假裝納入語意 |

USB3 初版只用 Wake／Reset 的政策未找到這批尾端，後來在開發資料中加入
「既有 Link 後的 Reset／非法 LFPS＋Polling」結構，並補正常／恢復反例。
所以兩個定位結果是開發資料回放，不能宣稱獨立盲測。
候選表示值得調查的組合；capture 結尾／缺口仍可能解釋後續未見 Link，沒有根因結論。

PD Cap 中 SourceCap 的12次 retry 已在原生 Transaction 分組內，不會重複計成12個故障。
DP Configure 的單次 NAK 保留為中性流程；Transfer8 起點 Packet158、回覆 Packet160，
各自時間／角色可核對。RDO 同時顯示 A／W 時不自行選單位或換算。

## 原生操作與限制

實測版本為 **10.40 Build6309**。`GotoUnit(0/1/3,index)` 對應 Packet／Transaction／Transfer，
API 返回與實際 GUI 核對分開記錄。當 API 沒有切換前景或 GUI 仍在其他層級，
工作區顯示 PKT／TRA／XFR 提示，由工程師手動切換。未把測試座標寫進產品。
原生 API 定義見 [LeCroy Trace interface](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/primary-dual-interface-for-trace)，
欄位來源見 [Input Context](https://manuals.teledynelecroy.com/usb-protocol-suite-manuals/v10.50/input-context-members)；
10.50 文件不等於10.50實機通過。

保留受限共存，拒絕接管已開啟的其他 LeCroy。來源與唯一唯讀副本檢查
SHA-256／大小／mtime／唯讀狀態；分析後副本移入綁定資料夾供導航，不重複複製。
超時不宣稱取消；清理未確認便停止下一段擷取，不強制關閉不明程序。

Walkthrough 修正了換檔殘留協定控制、空白分頁、預設選到無關空結果、
PD 原生單位列未預設選取等客觀問題。已觀察流程與候選分開顯示，並保留總數。
這些是程式及畫面檢查，不能取代一位不熟悉 trace 的真人操作。

## 驗證與證據位置

證據根目錄在 Git 外：
`C:\Users\reiko\.codex\visualizations\2026\10\16\01a14297-966e-7b51-b3e6-572fecb51b9e\usb3-pd-implementation-20261019`。
`slices.json` 保留逐片記錄；`exp01-*` 是原生定位，`u301-*` 是 USB3 擷取，
`pd01-*` 是五份 PD 原生群組／header，`pd03-native` 是實際工作區流程，
`final-u3-*`／`final-pd-*` 是最終程式回放。原始 capture、vendor include 及完整匯出不加入 Git。

首次 EXP-01 USB2 多候選誤用歷史報告而導航到296；沒有把它當372通過。
隨後使用目前 `final/fail_06` 報告重跑，562／372／446有獨立正確輸出與畫面。

本機驗證：

- `python -B -m unittest discover -s tests/usb_control_tool -v`：51項，含有檔案效果的
  單副本／分協定失敗、逾時 HTTP 可回應、拒絕過期／任意目標及正常反例。
- `python -B -m unittest discover -s tests/usb_control -v`：原31項；
  `python -B -m unittest discover -s tests/u01 -v`：原14項。
- C# 原生目標政策10項、預設協定6項、啟動路徑／內附 runtime12項。
- 包內 Python、PATH清空、工作目錄 `C:\Windows` 執行真實 CLI 回歸：
  FAIL01→1386、FAIL06→562／372／446、PASS04→無候選。
  三者 USB3／PD 均未觀察到本範圍事件，來源及唯一唯讀副本完整性通過。
- 原生可攜 EXE 在 PATH清空／不同工作目錄啟動，透過真實 picker 匯入 PD Cap，
  完成三協定 pipeline、自動選 PD 流程、預設選取原生群組，並核對交易與帶單位欄位。
  從「前後交易」切到未觀察到 USB2，會回到有解釋的「檢查提示」，不留空白。
- 用保存的真實模型回放最終 UI 的單候選／多候選／零候選／USB3部分資料，
  圖片為 `ui-final-*-replay.jpg`；這些是畫面回放，不是額外獨立 trace 或真人測試。
- 審查另發現已支援 PD 訊息若缺必要 header，需直接拒絕；補上反例後，
  重跑 PD資料／導引／pipeline共16項及五份實機資料，通過後重新封裝。
  此次封裝相對完整 GUI 測試僅增加該資料驗證 guard；原生 UI、擷取與導航來源相同。
  最終內附 runtime 再解析實際 Cap 匯出，9個 Transfer相符。
- ZIP CRC、manifest 60個檔案的 SHA-256／大小、包內與 repo 原始碼位元組一致。
  已檢查十份可行性原始來源的 hash／大小／mtime／mode，三份 USB2原始來源另由
  真實回歸檢查；凍結 USB2 engine／Automation／VSE／U01 host四檔未改。
  既有 PLAN／closeout 前綴與無關 tracked／untracked工作保留；自有視窗／worker正常結束。

套件為桌面的 `USB-Trace-Triage-USB3-PD-20261019.zip`，11,552,114 bytes，SHA-256
`952244bbb76a93e184c6d42bacba0c97211abb3adf3db228c95109e5a5ef19b9`。
內附 Python3.13.16；沒有 trace、vendor include或私有 raw證據。
`package-final.json`、`exp02-regression.json`、`preservation-current.json` 保留機器可讀紀錄。

已量測的 pipeline耗時：三份 USB2回歸約75.966／67.033／66.738秒；PD Cap原生工作區
首輪121.595秒。`resources.json` 記錄每個程序生命期峰值及每秒抽樣磁碟量，
不能把各程序峰值相加當同時使用量。這些數字沒有包含真人閱讀／核對，不能當成省時率。

## 待驗證，並非本機工作阻塞

1. 未參與規則調整的 USB3 trace；真實 GL3525 PD 正常／故障與混合協定 capture。
   目前只有型別／namespace合成測例，不據此宣稱真實混合 capture 已核對。
2. LeCroy10.50實機、乾淨 Windows、不同機器的安裝與完整擷取／導航。
3. 真人拖放、陌生 trace 找候選→理解→回到 LeCroy 的總時間、錯誤方向與結果正確性。
4. 自動原生顯示層級切換與安全多實例共存仍受限；首版明確使用手動層級及受限共存。

結論為「本機可做的工程切片完成，產品／外部資格化待驗證」。
保留既有 USB2歷史結果及人工驗收界線，不宣稱全面 USB3／PD支援、USB PASS或根因。
