# Flow-first 增量契約（FS-00～10）

本輪以本機 r6 為基準，新增觀察流程與調查建議，不改 G2/G3/G9、原生擷取或導航。
`pcie.flow-triage/v1` 保存 run/source/display/namespace、知識包 hash、方向觀察區間、情境來源、建議與 Packet 證據。
現有 stage summary 仍保存原始 typed observations；Flow 不回寫其事實，也不改原交易候選排序。

- 按已觀察 channel/direction/epoch 分區；沒有實體 Link 配對時不合併方向。
- 最後保留的里程碑與當前可用狀態分開。無效 LTSSM、較晚的斷線、範圍截斷不能被較早 L0 覆蓋。
- 非空情境必須有說明、來源與本次 source/display/namespace 綁定。全檔情境僅為背景；只有明示 channel/direction/epoch 與 Packet 起迄相符的 Link Down 才可標 EXPECTED_CONTEXT。
- 情境不刪除交易證據，不把 Completion 狀態或相似 Request 改成成功／失敗。沒有適用規範，本版不產生 SPEC_MISMATCH_CONFIRMED。
- Completion 先列出原生可見狀態；同 Key、逆向與同觀察區間只是關聯線索。缺完整 Split child mapping 時配對、timeout、retry、replay 都不成立。
- Flow 排序依未解階段與可定位證據；同級以最新保留階段優先，明示這是檢查順序。過往流程仍可展開，不湊三個故障。
- UI、HTML、Markdown 消費同一 flow presentation；phase locator 與 packet candidate locator 分開。USB 路徑不變。

知識包只有原創提示與公開來源引用。`sources.json` 固定 commit／版本，六張卡經 schema 與本地載入器雙重檢查。
未知 Gen／Mode 僅允許工程提示；Flit 不套用此版非 Flit 交易關聯。無規範性來源時，缺漏或散文不能提升為確定違規。

驗證以有情境／無情境相同事實、錯範圍／跨方向／跨 epoch、invalid/tail、SC/UR/CRS/CA、Tag recycle、tamper、真實 trace 離線重播與封裝原生 smoke 為主。陌生 trace／真人省時仍待驗證。

計畫所列 `pcie-observation-timeline-contract.md` 在本 checkout 不存在；使用現有 `pcie-inspection-observation-contract.md`、B1d/B1e/B2g 與 r6 typed source contracts，不虛構缺失文件。

2026-10-20 SKILL-FIX：每項 Flow next_action 的來源、適用範圍與降級行為由
`knowledge/pcie/next-action-contract.md` 定義，目錄為 `knowledge/pcie/next-actions.json`。
資料來源分為原生 trace_evidence、公開欄位/工程指引與本地工程政策。
缺來源、未核對章節或不適用範圍只產生 EVIDENCE_REQUEST/NOT_EVALUATED；不改協定事件、候選、階段分區或排序。
桌面既有「限制與來源」、HTML、Markdown 顯示逐 action 來源；舊 r7 保存模型須用原封裝讀取，不能套用新知識包後宣稱 byte-identical。
