# PCIe Next Action 來源與適用契約

版本：2026-10-20/v1。這是本 Repo 原創工程政策，不是 PCI-SIG 規範，也不能提供裝置專屬接受條件。

<a id="evidence-scope"></a>
## 保留觀察範圍

每個建議綁定本次 source/display SHA-256、packet namespace、channel、direction、observed epoch、phase、Packet 範圍與原生 evidence refs。Device/BDF 的實體身分及 physical Link 配對沒有獨立證據就寫 UNKNOWN。時間先後、相同 Key、單方向 L0 不能自行建立因果、Retry、雙向 Link 或初始化完成。

<a id="phase-review"></a>
## 階段覆核

較早區間只作背景；到同方向較晚區間核對觀察，不沿用跨 epoch 狀態。有效單方向 L0 之後可以提出核對 Config/Completion 的工程建議，但必須先確認 Link/epoch、目標與外部裝置辨識資料。invalid、Recovery、斷線或截斷都不能由較早 L0 蓋過。本政策只定義查證流程，不宣告 PCIe 規格門檻。

<a id="source-claims"></a>
## 來源與主張分類

每項 action 包含 rule_ids、source_refs、applicability、required_evidence、limitations、trace_evidence 及 claim_kind。知識來源是 FIELD_REFERENCE、VENDOR_GUIDE、MODEL_REFERENCE 或 LOCAL_ENGINEERING_CONTRACT；trace_evidence 只代表本次觀察。現有 action 僅支援 ENGINEERING_RECOMMENDATION 或 EVIDENCE_REQUEST，沒有 SPECIFICATION_FACT 或規範違規判定。

來源必須有直接章節/行號、固定 revision、支持內容及不能支持的事項。本地契約核對內容 hash 及 anchor；上游網址在 runtime 不下載，reference match 只代表符合本次已審來源記錄，不是重新核實遠端內容。13.42 手冊不能單獨證明 13.26 API/GUI 行為；FPGA/Linux/模擬模型不能當成未知 Windows 裝置的規範。引用清單不等於全部前提成立。

<a id="data-requests"></a>
## 補充資料

缺來源、revision 不符、來源 locator 無效、模式/phase 不適用或 scope 未綁定時，action 降為 EVIDENCE_REQUEST，evaluation 保持 NOT_EVALUATED。顯示缺口，不能沿用未獲支持的操作指令。這只是請求證據，不宣告 PCIe FAIL 或 PASS；保留獨立 Packet findings 與 UNKNOWN。

操作 marker、OS 裝置辨識紀錄、實體拓撲/BDF 對應可作可選的外部佐證；尚未取得時只請求補充。沒有平台文件時不指示工程師使用特定 BIOS log 功能、不推定 BIOS log 一定存在。資料取得方法由工程師與平台文件決定。

<a id="vendor-policy"></a>
## ASPM 產品條件

pci_regs.h 僅支持欄位定義，不能證明 vendor 命令、設定生效時間、讀回語意或產品期待。未提供適用裝置的 vendor 文件、操作時間、目標/Link/epoch 與預期行為前，ASPM 只列「建議補充資料」，不得開始規範符合性判定。取得資料也不自動升格為規範；需要獨立審查來源及適用性。

<a id="compatibility"></a>
## 相容性與驗收

新增 action metadata 與保守文字不改 PCIe 協定規則、原始事件、交易候選、phase 分區、排序或定位。knowledge pack hash 隨來源契約變更；舊 r7 ZIP/保存結果不覆寫。JSON、HTML、Markdown 與桌面候選保留 action provenance；所有工程指引均維持不高於 GUIDANCE_ONLY。
