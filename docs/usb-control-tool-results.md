# TOOL 實作與本機驗證紀錄

2026-10-16。使用者已核准 r2 並授權依切片實作；後續親自操作回報 UI 難用及跳出
瀏覽器，要求先研究同類工具。已讀官方 Saleae、Wireshark、Total Phase 與 Windows
介面文件，並以同一原生工作區取代舊入口／外部瀏覽器組合。

## 現況

| Slice | 本機交付與驗證 | 尚未通過的部分 |
| --- | --- | --- |
| TOOL-01 | 本機 controller、具 message pump 的 STA worker、來源綁定、候選白名單、重用開檔、非同步狀態與操作耗時；受限模式拒絕接管既有工作 | 安全多實例共存未證明；前景切換受 Windows 限制；實際 COM 永久掛住及所有競態未完整資格化 |
| TOOL-02 | 原生 FileDrop／選檔與私人 stdin IPC；選檔→VSE→既有排名→原生候選工作區→定位已實測 | Computer Use 跨視窗 drag API 拒絕出界座標，未資格化實體 Explorer 拖放 |
| TOOL-02.5 | 取得使用者親自操作的具體負面回饋，作為 UI 修正依據 | 新版需真人重測，未標為 PASS |
| TOOL-03 | 單視窗候選／提示／前後交易／來源限制、原生定位及 HTML 匯出；改善狀態、候選總數及換檔顯示 | 客觀缺陷已修，易用性與視覺認可仍待使用者確認 |
| TOOL-04 | 13 個明列來源檔的試用 ZIP，manifest／CRC／逐檔 bytes 驗證，新目錄解壓後從其他 cwd 啟動；記錄最大批內 trace 的耗時與資源 | 不是獨立乾淨 Windows 環境；未內建 Python／LeCroy；54 MB 不是普遍大型 trace 性能驗收 |
| TOOL-05 | 保留前輪盲測與人工記錄方式，不調整開發資料排名 | 未取得陌生 FAIL/PASS 或工程師總任務時間，尚未執行 |

工具可以本機試用；不能稱為所有切片或產品驗收通過。沒有 commit、push、PR 或
merge。既有 dirty work 與凍結分析來源保留。

## 驗證

- HTTP 與私人 native IPC 的候選授權、Host／Origin／token、舊 case、任意 path/unit
  拒絕、重複操作、改檔保護、無回應子程序、實際 Windows mutex、PS5 module
  環境隔離：15 項通過。既有 USB control 31 項、U01 14 項通過，共 60 項。
  這些不是 USB 協定／工程師驗收的替代品。
- 實際瀏覽器報告按鈕定位 FAIL_01 1386、FAIL_06 562→372→446；同候選重複操作
  open_count=1。原生新版工作區再次經實際選檔分析 FAIL_06，三個候選均逐點核對
  原生 Transfer、時間及 Address/EP，仍為同一副本／同一次 OpenFile。
- FAIL_01：1386／35.611541400 s／13/0。
  FAIL_06：562／40.351786032 s／19/0；372／27.608155682 s／5/0；
  446／33.191925582 s／12/0。
  原生 Packet/XFR 顯示層級可能需手動切換；Computer Use 帶到前景不等於橋接成功
  帶到前景。部分 worker 前景請求回傳 false，介面有手動切換提示。
- 工具開著自己的另一份受控 trace 時，新定位在 COM 啟動前被拒絕，原 trace 和
  位置不變。這是受限模式通過，不是多實例共存通過。
- 對已核實 PID、啟動時間與唯一副本名稱的自有 LeCroy 做故障注入後，後續定位
  停止接管，HTTP 仍有回應，End 完成清理；另以真實無回應子程序測 transport
  timeout。沒有把此結果稱為真實 COM 掛住的完整恢復測試。
- 新的 FAIL_01、FAIL_06 擷取模型與凍結模型相同（只排除每次原始擷取結果 hash）。
  沒有使用 FAIL 名稱或已知時間引導自動搜尋，未增加／調整分析規則。
- FAIL_06 新版實際分析約 22.1 秒；工作目錄抽樣峰值 54,139,214 bytes；
  controller／擷取 wrapper／LeCroy 各自 OS 生命週期記憶體峰值約
  29.7／104.8／595.2 MB。這些峰值不可加總成同時用量；不含人工讀報與核對。
- 新解壓目錄的 PASS_04 選檔分析成功，原生空結果畫面保留分析範圍及非 PASS 說明，
  沒有開啟外部瀏覽器。新目錄不代表乾淨 OS。

實作時修正了 child process 繼承私人 stdin，以及 PS7 module path 滲入 PS5 導致
Get-FileHash 不可用兩個整合問題。錯誤日誌保留；未修改凍結 runner 或 COM host。

## evidence_refs

本機證據根目錄：
C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/tool-implementation/

- before/ 與 git-status-before.txt：本輪前既有 dirty state。
- tool01-fail01/、tool01-fail06/：按鈕、操作、綁定、完整性與原生落點。
- ipc-isolated-env/、native-fault-injection.json：實際分析與自有 native crash。
- native-workspace/：新版 FAIL_06 的選檔分析、三次原生定位、資源與關閉紀錄。
- native-workspace-fail06.png、native-workspace-goto-562/372/446.png 與同名 JSON。
- native-workspace-pass04.png：新解壓包原生空候選結果。
- final-verification.json：凍結 11 檔、9 份來源、既有文字前綴、綁定副本及包內來源。
- USB-Trace-Triage-native-20261016.zip：試用候選，僅程式／說明／manifest，無私有 trace。
- fresh-unpack/USB-Trace-Triage/：實際新目錄啟動副本。

原型既有 PASS 範圍保留；本輪 UI 負面回饋不否定原型已證明的候選能力，
也不構成已驗證產品價值。新版下一個人工關卡是同一視窗流程的重新操作。

## 2026-10-16 TOOL-03 視覺調整與攜帶版修復

本節更新上述 source-only 包的交付狀態。使用者確認布局可保留，要求中性淺色、
依工作狀態決定主按鈕，並回報另一台 10.50 電腦啟動無反應。現已建立內附
Python 3.13.16 x64 與預編譯 EXE 的攜帶版，不要求收件人另裝 Python 或設定 PATH。
啟動器直接顯示原生檢查視窗、寫入持久日誌；先查預設 LeCroy 路徑及兩個 registry
view，找不到執行檔才請使用者指定。COM 未註冊或不匹配會明確提示修復安裝。
未修改執行原則、登錄或接管既有 LeCroy 工作。

視覺修改集中在原生色彩 Token、主／次操作、頁籤、候選選取與按鈕互動狀態。
空白與無候選以匯入為主，有候選以定位為主，錯誤以恢復方式為主；錯誤時不再
顯示「從一份 Trace 開始」的初始內容。無候選狀態明確說明分析範圍及非 PASS。
白字／主按鈕對比 5.38:1、hover 6.66:1、pressed 7.87:1；次要文字／白底 6.19:1。
按鈕焦點採 2px 內框；不把主觀美觀分數或這些計算當作完整 WCAG／真人驗收。

攜帶版整合過程實際重現了一次開檔回歸：使用者匯入 FAIL_06、FAIL_03 時，
LeCroy OpenFile 回報工作副本路徑不正確，尚未執行分析。原因是新建的 AppData
目錄尚未解析 MSIX 檔案系統重新導向；COM 程序無法看到呼叫端的虛擬位置。
建立後解析實體路徑已修正；啟動日誌與工作目錄也使用實體路徑。
同一環境可重現建立前後 resolve() 不同，並有實際檔案的回歸測試。

驗證：

- 18 個 controller／攜帶包測試通過；既有 USB control 31、U01 14 通過。
- 原生啟動合約 harness 12 項斷言通過：帶空白引號的 registry 命令、預設路徑
  優先、registry fallback、找不到的結果、缺 Python 錯誤與日誌、實體目錄、
  實際內附 runtime 載入。未改寫真實 registry，也未以 harness 啟動 COM。
- 官方 Python ZIP SHA-256 核對、ZIP CRC、manifest 逐檔 bytes、PSF LICENSE 保留。
- 清空 PATH、從其他 cwd 啟動攜帶版，原生工作區成功出現。這不是乾淨 Windows 驗收。
- 修正後透過攜帶版 Python 在 AppData 新建工作目錄重跑實際資料：FAIL_01 → 1386；
  FAIL_06 → 562、372、446；PASS_04 → 無候選。三份來源 SHA-256 不變。
  此三次為實際擷取／分析驗證，不宣稱三次全部經過 GUI 選檔操作。
- 分析規則、排序、Automation adapter、VSE 及 COM host／導航來源未修改。
  runner 只增加已偵測執行檔位置的 metadata 路徑支援。

10.50 的遠端「完全沒回應」原始根因尚未取得；本機虛擬路徑回歸與遠端啟動問題
分別記錄，不能推論為同一原因。官方 10.50 仍列出 CATC.USBTracer，不能代替
遠端實機重試。完整人體操作、獨立乾淨 Windows、陌生案例與省時驗收仍待完成。

本輪 evidence_refs：同一外部根目錄下 tool03-portability-20261016/，包含 before/、
portable-real-runs.json、startup-fixtures-r2/startup-fixture.log、官方 runtime ZIP、
初版失敗及修正版本試用包。AppData 的失敗工作與成功工作均保留，未覆寫。
