# USB3／PD 試用版操作

2026-10-19。這份說明適用 `usb3-pd-trial-20261019`。本機已測 LeCroy
10.40 Build 6309；10.50、新機器及真人省時驗收仍待確認。

## 開始分析

1. 將整個 ZIP 解壓縮到可寫入資料夾，執行 `USBTraceTriage.exe`。
   已內附獨立 Python，不需要安裝 Python 或修改 PATH。
2. 按「匯入 Trace」選一份 `.usb`，或使用既有拖放入口。
3. 工具製作一份唯讀工作副本，依序分析 USB2 EP0、USB3 Link／LFPS，
   有 PD 封包時再擷取 PD 原生 Transaction／Transfer 與最小 header。
4. 從左上協定選單查看各組結果。各組最多三個優先候選，顯示完整候選數。
   預設先開有候選的組別，否則先顯示失敗或部分缺漏，避免把資料缺漏藏起來。

若 LeCroy 已有其他工作，工具顯示受限共存訊息，不接管或關閉既有視窗。
請先自行保存既有工作，再安排分析。COM 等待期間工作區仍回應；超時並不等於已取消。
清理未知時，先確認 LeCroy 狀態及工作資料夾的日誌，再重新執行。

## 看候選與原始證據

候選包含位置、事實、推薦理由與下一步。「前後交易」可核對原生欄位；
「限制與來源」列出各協定狀態、擷取數量、缺漏、版本和來源 SHA-256。

PD 另有「已觀察流程（非候選）」入口，供查看正常協商、Discover、Enter Mode、
DP Status／Configure。即使單次 NAK 或 Cap Mismatch 沒有觸發候選，仍能看到並定位。
最多列出 24 個流程，同時保留完整數量；它們不佔候選排名，也不代表已確認故障。
角色只在適用 SOP 情境呈現，空 duration、未知欄位與重複欄名不會自動補值。
電壓／電流／功率保留 LeCroy 原生帶單位值，不將 RDO 並列電流／功率字串自行換算。

## 回到 LeCroy

選擇候選或中性流程後，按「在 LeCroy 定位」。PD 可從按鈕右側選單切換
Transfer、起始 Packet 及已核對的 VDM 回覆 Packet。重複定位沿用同一份副本與工作階段。

目前 `GotoUnit` 無法保證 GUI 自動切到所需層級。工具會明確提示：
Packet 請選 **PKT**，Transaction 選 **TRA**，Transfer 選 **XFR**。
請在 LeCroy 核對副本、編號、時間、channel／SOP／角色；API 成功返回不能取代畫面核對。
「複製位置」可保留人工定位資訊；「匯出 HTML」只輸出離線報告，主要操作仍在原生視窗。

## 如何判讀沒有候選

| 狀態 | 工程意義 |
| --- | --- |
| 已分析 | 完成本版本支援範圍的分析；零候選不能當成 USB PASS |
| 未觀察到 | 本次資料路徑沒有看到適用事件；CC 事件不代表有 PD 訊息 |
| 資料部分缺漏 | 已達輸出上限或欄位／群組不完整；停用依賴未見後續的規則 |
| 尚未支援 | 此範圍未實作，不提供正常判定 |
| 執行失敗 | 該協定分析未完成，查看日誌與恢復方式 |

USB3 Link＋LFPS 最多保存 300000 筆，PD header 最多 50000 筆；全程計數仍保留。
USB3 不推測精確 LTSSM state；PD 只做 SOP 基本協商／VDM 結構導引。
PPS／EPR／role swap／extended、電氣／Eye、USB4、完整 bulk／streams、
合規與根因判定未涵蓋。不同協定時間接近不等於存在因果。

原始 `.usb` 不會存回；副本與來源均核對 hash、大小、mtime 及唯讀狀態。
可在工作資料夾查看 `inspection.json`、`report.html`、各協定 raw、
`integrity.json`、`resources.json` 與導航日誌。分析／API 耗時已記錄，並非真人省時率。
