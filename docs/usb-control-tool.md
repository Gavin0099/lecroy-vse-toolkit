# USB Trace Triage Tool 試用說明

2026-10-16。本機工程師試用候選；尚未通過完整產品驗收。

## 開始

1. 使用 Windows 10/11 x64、Windows PowerShell 5.1、.NET Framework 4.8，
   並安裝及註冊 LeCroy USB Protocol Suite 的 Automation/COM。
   本機已驗證 10.40 Build 6309；10.50 官方仍提供 CATC.USBTracer，實機相容性待重試。
2. **攜帶版請解壓縮整包，雙擊 USBTraceTriage.exe**。內附 Python 3.13.16 x64，
   不需要另裝 Python、不需設定 PATH，也不會安裝 Python 到系統。
   啟動器先顯示檢查視窗，檢查預設 LeCroy 路徑及 32/64 位元 COM 註冊；
   都找不到 UsbSuite.exe 時才請使用者指定。若 COM 未註冊，請用 LeCroy 安裝程式修復。
   不自動改系統執行原則或登錄。攜帶版包含預編譯原生入口；CMD 也會轉啟動該 EXE。
   原始碼 checkout 的 CMD 備用路徑仍需已安裝 Python，失敗時保留主控台訊息。
3. 在原生工作區按「匯入 Trace」或拖入一份 .usb。結果直接顯示在同一視窗。
4. 左側選候選，右側閱讀下一步、事實與理由。前後交易、證據缺口分別在分頁。
5. 按「在 LeCroy 定位」，核對唯讀副本名稱、Transfer、時間及 Address/EP。
   若 LeCroy 顯示 Packet 層級，按原生 XFR 工具列切換到 Transfer 層級。
   Windows 可能拒絕切換前景，此時手動切至 LeCroy。
6. 「匯出 HTML」另存離線報告，日常查看不啟動外部瀏覽器。
   「工作資料夾」可取得日誌、副本、模型與完整性紀錄。
7. 換檔會先釋放本工具的定位工作。關閉工具也會檢查來源與副本，再釋放工作。

分析期間不宣稱已取消原生呼叫。無回應／清理未知時停止重試；保留工作資料夾，
由工程師確認自有 LeCroy 工作狀態後再開始新工作。

## 共存限制與資料範圍

目前採受限共存模式：若 LeCroy 已有工作階段，擷取及初次定位會拒絕接管。
工具不自動關閉使用者的 LeCroy；請先自行保存既有工作，再安排獨立測試。
沒有證據支持多實例隔離，也未保證所有競態與原生當機都可自動恢復。

只涵蓋 USB2 標準 EP0 控制傳輸。候選是優先調查提示，未判定根因或 USB-CV 合規。
無候選不代表 USB PASS。最多顯示三個候選，並保留總數與未顯示數。

原始 trace 不交由 LeCroy 開啟；工具使用唯讀工作副本。來源與副本會檢查
SHA-256、大小、修改時間及唯讀狀態。這是已測路徑的完整性保護，不是作業系統層
不可變儲存。工作目錄保留 trace 副本與原始擷取資料，請按專案規範保存或清理。

## UI 參考與實作決策

使用者親自操作後回報「UI 很難看，點選後仍出現網頁」。此回饋列為 TOOL-02.5
的實際缺陷，不能據此宣稱早期操作驗收通過。已先查官方文件，再修改可見流程。

| 官方參考 | 採用方式 |
| --- | --- |
| [Saleae Logic 2 工作區](https://www.saleae.com/support/logic-software/viewing-and-analyzing-data/navigating-the-software) | 清楚的主工作區、少量主要操作、次要資訊按需顯示；不複製波形 viewer。 |
| [Wireshark 主視窗](https://www.wireshark.org/docs/wsug_html_chunked/ChUseMainWindowSection.html) | 候選選取與右側細節連動，保留可核對的原始欄位。 |
| [Total Phase Data Center](https://www.totalphase.com/support/articles/200424386-data-center-software-user-manual/) §5.3 | 交易、詳細資料與操作狀態在同一個應用程式中。 |
| [Windows 設定指南](https://learn.microsoft.com/en-us/windows/apps/design/app-settings/guidelines-for-app-settings) | 常用操作保留在工具列；不把開檔、定位埋進設定頁。 |

視覺採白色閱讀區、淡灰背景、單一藍色主操作；候選分區固定，詳細內容可捲動。
原生 WinForms 的 TableLayoutPanel / SplitContainer / ListBox / TabControl /
DataGridView 直接呈現既有 inspection JSON；保留 Python／PowerShell 分析及 COM
worker。沒有引入 Electron、Qt 或 WebView2，也不修改凍結排名。
[TableLayoutPanel 官方文件](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.tablelayoutpanel)
與 [SplitContainer 官方文件](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.splitcontainer)。

WebView2 可把 HTML 嵌入 WinForms，但需要 SDK 與 runtime；僅嵌入原頁不能解決資訊
層次。[Microsoft 官方整合方式](https://learn.microsoft.com/en-us/microsoft-edge/webview2/get-started/winforms)。
本次選擇原生呈現，是基於目前 Windows 範圍與既有入口；不是其他框架的效能判定。

目前沿用布局，以語意 Token 集中管理淺灰 #F5F5F5、白色閱讀區、文字 #242424、
主要操作 #0F6CBD。空白／無候選以匯入為主，有候選改以定位為主，錯誤以恢復方式為主。
候選保持中性、選取用藍色側線；紅色只用於操作錯誤。按鈕具 hover／pressed／disabled／
focus 狀態，頁籤以底線表示選取。白字／藍底對比約 5.38:1，次要文字／白底約 6.19:1。
工程師易用性與時間節省仍須真人驗證，不採主觀美觀分數作為驗收。

## 本機紀錄

啟動日誌位於 LocalAppData/LeCroyTraceTriage/startup/startup-*.log；失敗對話框顯示完整路徑。
從 MSIX 應用程式啟動時，Windows 可能將 AppData 重新導向到套件 LocalCache；
工具會先解析實體路徑，讓 LeCroy COM 及檔案總管存取同一份檔案。
每次建立新的 run-* 工作目錄，不覆寫舊結果。
operations.jsonl 記錄分析／定位操作與耗時。analysis-*/resources.json 是每秒抽樣
的工作目錄大小及程序各自 OS 生命週期記憶體峰值，不能加總成同時峰值。
完整操作時間、工程師看到封包的時間及錯誤方向仍須人工實測。

攜帶包可由以下命令重建：

```powershell
python tools/build-usb-control-tool.py --runtime-zip Python官方embeddable.zip --output 新的.zip路徑
```

建置器核對官方 Python 3.13.16 x64 ZIP 的固定 SHA-256，保留 runtime/LICENSE.txt，
只調整隔離的 python313._pth 加入本工具 tools 目錄；不載入使用者 site-packages。
官方來源：[Python 3.13.16](https://www.python.org/downloads/release/python-31316/)。
未指定 --runtime-zip 時只能建立原始碼包，不能稱為含 Python 的攜帶版。
包內 manifest 記錄每個檔案的 SHA-256；不收集整個 dirty repository。
