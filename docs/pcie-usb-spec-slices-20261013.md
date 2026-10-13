# PCIe／USB 規格研究後的 slice 計畫

日期：2026-10-13。原審查決策為 **APPROVE WITH CHANGES**、第一輪只放行 S01。使用者後續指示「review 沒問題就做下一個 slice，按照這樣的步驟做下去，不用一直停下來」，已放行唯讀 runtime 與後續逐片實作／驗證／review；通過適用前置條件即可接下一片，不再逐片詢問。資料、規格正文、工程師定義與實際資格化門檻仍保留，未通過者不得宣稱完成。最新指示「先push上去」授權必要 commit／push，範圍見 [push checkpoint](slice-push-checkpoint-20261013.md)；沒有授權 merge、硬體操作或跨 checkout 搬動成果。

這次將官方規格、ECN／errata、測試規範、LeCroy 手冊／範例，以及 OS 錯誤記錄文件，對照兩個 checkout 的實際能力。結論是有一批不依賴工程師產品規則的工作可以先準備；先補輸入覆蓋、欄位與原生交易輸出的證據，再加入有來源的分析規則。

來源入口與閱讀深度見 [來源地圖](pcie-usb-source-map-20261013.md)，完整來源 ID、版本、章節、取得限制與檔案身分見 [來源登錄](pcie-usb-source-register-20261013.json)。登錄包含目錄及尚未取得的規範，不能把來源數當成全文已讀數。本計畫也不是全套 PCI-SIG／USB-IF certification checklist。

## 本輪授權決策

| 狀態 | Slice | 目前允許的工作與下一道門檻 |
| --- | --- | --- |
| **LOCAL PASS** | **S01** | 離線契約與測試已完成，review 未發現阻擋問題；不表示真實 trace 或協定資格化。 |
| **BOUNDED ACCEPTED** | **U01、P01、U02、U03、P03、P10、P11** | 原生 transport／抽樣欄位、standard register raw view 與 valid state points 已逐片 review；缺 mode、完整 coverage 或特殊樣本的部分仍未資格化。 |
| **SOURCE BLOCK ACCEPTED** | **I01、I02** | 已將 P03／U02 接入各自報告；既有 W1–W5／C5 結論保留原範圍，沒有新增 opaque verdict。 |
| **資料門檻 HOLD** | **U04、U05、P02** | U04 缺精確 state 欄位；U05／P02 缺 explicit child packet references。 |
| **CANDIDATE，逐片選擇** | **P04–P09、U06–U11、O01–O02、G01–G02** | 最新授權允許依證據逐片實作；缺規格正文、適用輸入或工程師定義時保留門檻。P10／P11 已到達限定觀測 checkpoint，未擴至全部模式與電氣／政策判定。 |

下文的建議順序是後續依賴關係，不是本輪工作清單。S01 的 validator 不會呼叫 LeCroy／COM／GUI、開啟 CATC、執行 extractor／protocol evaluator、收集 trace 或搬動 checkout。W1 v1 維持 frozen；本輪沒有把 manifest 資訊塞進 W1 opaque 欄位以取得新語意。

## 1. 先承接已做的工作

| 已有能力 | 本次核對的證據 | 新工作如何承接 |
| --- | --- | --- |
| USB 合併抽取、比較、來源與工作副本完整性 | [DEMO-2 integrity closure](demo-2-integrity-closure-results.md)、[時間精度](c3-timestamp-fidelity-results.md) | 保留原 PASS 的 trace／版本／執行方式範圍。新欄位與選取條件另驗，不推翻既有結果 |
| PCIe DLLP／TLP 部分欄位 | [B1a](pcie-b1a-evidence.md)、[G2a](pcie-g2a-evidence.md)、[G2b](pcie-g2b-evidence.md) | 只補 PSN、credit、原生 grouping 等未資格化部分 |
| ERR message 與鄰近事件關聯 | [G3c-0](pcie-g3c0-evidence.md)、[G3c](pcie-g3c-evidence.md) | 已有 message extraction／mapping；實測確認的例子是 ERR_COR，不能說三種 ERR 都已實測。新增 AER／DPC 的狀態證據 |
| MUX 接通／雙向 L0 的 bounded PASS | [B1d](pcie-b1d-evidence.md)、[工程師問題](pcie-b1d-engineer-questions.md) | training timeout、TS-error tolerance、Gen3 convergence、hot-plug completion 四項驗證債各有限制，不重開整個 B1d |
| Config access、capability、observed state、query／diff | [B2c](pcie-b2c-evidence.md)、[B2d](pcie-b2d-evidence.md)、[B2f](pcie-b2f-evidence.md) | 以既有事件與 bit／byte validity 語意延伸；不重造 baseline |
| Config Space API 與 sidecar | [B2h1](pcie-b2h1-cfgspace-api-evidence.md)、[較新的 B2h2](pcie-b2h2-sidecar-evidence.md) | 目前只到一個 trace、BDF 256、before_disconnect、LinkControl。COM `bytes_set` 依 B2h2 實證是逐位元 mask，不能沿用 B2h1 的逐位元組說法 |
| PCIe W1–W5 event contract、timeline、MD／HTML observation report | PR #19–21 已交付；2026-10-13 `git ls-remote origin refs/heads/main` 確認 `f417eecb340f56d09d6e4c0ca0b86f81e2977181` | 使用已交付架構；本地舊 PLAN 的「B3 未開始」不代表 main 尚未完成 W1–W5，但整體 B3 的 spec／產品判定仍未完成 |

兩個 checkout 不互為完整超集：目前工作目錄 HEAD 是 `c100ee1bba49c0e1956c726e287ff5158e70aec5`，含 tracked G3／runtime 與 untracked B2h 等工作；乾淨 delivery checkout 是 `f417eecb340f56d09d6e4c0ca0b86f81e2977181`，已有 W1–W5，但缺部分前者的 runtime／G3 檔案。後續每片先列明所需檔案與證據來自哪個 checkout；本次沒有搬檔、merge、reset 或重新交付。雙 checkout 定位已在本輪完成，不另外安排一次相同盤點。

W1–W5 的精確入口在 delivery checkout：`scripts/pcie/b3a_event_contract.py`、`b3b_unified_timeline.py`、`b3d_observation_report.py`，以及 [W1 契約](C:/Users/reiko/.codex/worktrees/pcie-slice-delivery/lecroy-vse-toolkit/docs/pcie-observation-timeline-contract.md)、[timeline](C:/Users/reiko/.codex/worktrees/pcie-slice-delivery/lecroy-vse-toolkit/docs/pcie-unified-timeline.md)、[MD／HTML 報告](C:/Users/reiko/.codex/worktrees/pcie-slice-delivery/lecroy-vse-toolkit/docs/pcie-observation-report.md)。本機路徑只是目前定位，後續以已核對的 commit 與 repo-relative path 重新定位，不能假設永久存在。

## 2. 這次研究改變的實作順序

1. **覆蓋條件先於「缺事件」判斷。** USB VSE 手冊 LC-04 p168／170 記載，`SendTransfer()` 預設只送 completed transfer，bad-CRC packet 預設不送。PCIe／USB `ExportToText` 也受 display-hidden packet 與有效 range 影響（LC-02／05）。這是新分析的必要前提，尚不能反推舊 run 確實漏了哪一筆。
2. **先驗 LeCroy 原生交易輸出。** PCIe `_LINK`／`_SPLIT`（LC-01／13／14）及 USB `_TRA`／`_XFER`（LC-04／10／11）已有文件／範例。先確認輸出與適用性；只有具體缺口才寫自己的重建器。原生結果與自家結果可能共用底層解碼，兩者一致不等於獨立規範真值。
3. **USB command 已有候選 probe 欄位，LTSSM state 還缺精確欄名。** LC-04 p32 有 `LnkCmd`、`LinkCmdInfo`、CRC5 等欄位；LC-09 有 `GetLfpsDesc`。目前只找到 `_USB3_LTSSM_STATE` event，未找到專用 state member；不能猜 `in.State`。
4. **規則須綁版本與適用條件。** PCIe 公開 VSE 手冊 13.40 不等於本機 13.26；USB executable 10.40 也不能抹去手冊 v9.12／適用 10.13+ 的版本資訊。USB3.2 ECN 包內許多文件針對 base 1.0，需先查是否已納入 base 1.1。
5. **公開測試摘要不能補出未知門檻。** PCI-30 的 Relaxed Detect Timing 只涉及指定速度能力下 Fundamental Reset 結束到 Detect 的條件，不是泛用 training timeout。PCI-19 已把 LL/TL 54-20 Bad ECRC 改為 informative。公開簡報 PCI-18 不能獨自建立完整 compliance verdict。

## 3. 各片共用的驗收規則

最新授權允許逐片完成下列驗收，再 review 並接下一片；不把本計畫當執行證據。S01 仍只驗 metadata；runtime 證據屬各自後續 slice。前置驗收通過只是下游必要條件，仍須符合適用範圍與輸入門檻；單一分支缺資料不把無關分支自動改成失敗。

**輸入與 probe（Q-P）**

- 保存 source／工作副本 SHA-256、suite／script／constants 版本、protocol／Gen／lane／Flit mode、方向／port role、device／epoch、requested／effective range、display filters、selection flags、capture 起訖與中斷狀態。
- trace 執行承接既有 source-preserving read-only 模式，前後檢查來源與工作副本。不得直接在唯一來源執行。parser 僅讀既有輸出時，保存輸入雜湊與禁止覆寫輸出。
- 欄位能力（field capability）與事件觀測（event observation）分開記錄：前者描述此版本／mode／level 是否有來源或已資格化的欄位，後者描述這份 capture 是否實際看到相符事件及有效值。保留 raw value、單位、有效 mask、vendor packet index 與 level；`not observed` 不得直接寫成 `not supported`。callback／row／packet count 不互相當分母；應有結束標記與分層計數。
- 同一受控輸入兩次抽取應有相同語義輸出；代表性欄位需以精確 packet／原生顯示或已審核資料交叉核對。沒有某類事件的 trace 不能資格化該類欄位。文件存在與 runtime 可用分別列狀態。

**離線規則（Q-E）**

- 每條規則列 source ID、版本、精確章節、適用條件及已讀內容；metadata-only、公開摘要或教程不足以支援未公開的數值門檻。PCIe Base／errata 的正文 gate 未解時，可做欄位與描述性觀測，不能補造 strict PASS／FAIL。
- fixtures 的預期值來自規範例子、獨立人工標註／審核的 raw 序列或不變量，不可複製 production logic。至少有正常、刻意違反、邊界與不足證據案例；實際執行 evaluator，不能只檢查 mock 被呼叫。
- 缺資料、partial mask、capture 中途開始／結束、reset／device change、亂序／重複／截斷、sequence wrap、時間精度不足都要有明確處理；不把 UNKNOWN 轉成 0、不把 not observed 轉成 absent。
- 規則結果是該條件下的觀測或異常，不自動升格為裝置不合規、產品政策違反或 root cause。意圖、讀回、CATC 合併值、vendor-derived grouping 與 raw packet 分開保存。

### Trace eligibility matrix 與兩維度證據

每個候選 probe／adapter／evaluator 要先列「所需條件—輸入證據—是否適用」矩陣，按規則或事件類型決定可適用、不適用或未知。S01 只離線驗證這種宣告的格式、缺值與相容性；它不會靠 manifest 自行證明 capture 真的含有所需事件。具體 schema、欄名、版本與 validator 行為以 [S01 離線契約](s01-offline-contract.md) 為準。

| Eligibility 面向 | 需要記錄／對照的證據 | 缺值或不相符時的 gate |
| --- | --- | --- |
| 協定與 operating mode | USB2／USB3、PCIe Gen／Flit、lane、direction／port role，以及規則適用版本 | 已知不同則該規則不適用；未知則停止該規則判定，不跨協定填預設值。 |
| 身分與連續性 | source／working-copy identity、device／BDF／endpoint、epoch、capture 起訖／中斷 | 身分或 epoch 不能對齊時，不跨 reset／裝置重用合併；未知不視為連續。 |
| Selection／coverage | requested／effective range、filters、event levels、completed／incomplete、bad-CRC flags、分層 counts／end marker | 未證明選入的事件類型不能拿「沒看到」作負面判定；不把 manifest 宣告當 runtime coverage 已驗證。 |
| 欄位能力 | suite／script／constants／手冊版本、event level、field mapping、raw／unit／mask 的來源與 qualification | 文件記載只到 documented；未資格化、unsupported 或 partial validity 分別保留，擋依賴有效欄位的計算。 |
| 相符事件與上下文 | 該 trace 中實際 observed event、packet refs、雙向序列、payload／status／初始基準 | 沒有代表性事件只能保留靜態契約；缺 FC 初始基準、對向 ACK／FC 等條件時，停止對應數值或缺席判定。 |
| 時間與規則依據 | timestamp 精度／clock relation、已讀條款、版本與 ECN applicability、獨立 fixture | 不足時只呈現有來源的觀測／未知；不補造 timeout、協定 PASS／FAIL 或 root cause。 |

| Field capability | Event observation | 可以聲稱的範圍 |
| --- | --- | --- |
| 文件有欄位，尚未 runtime 資格化 | 沒有相符事件樣本 | 已找到候選欄位；不能聲稱可抽取，也不能判斷此事件不存在。 |
| 已在指定版本／mode／level 資格化 | 本 trace 沒觀測到相符事件 | 保留既有欄位能力；事件只記 not observed，並附 coverage。不能反推欄位不支援。 |
| 欄位未支援或未知 | event identity 已觀測到 | 可保留事件出現及原始參照；不合成未知欄位值或 state 名稱。 |
| 已資格化且有效值可用 | 本 trace 有相符事件及足夠上下文 | 只放行條件相符的觀測／規則；仍不等於全 trace、產品或協定通過。 |

「沒有事件的 trace 不能資格化該類欄位」與「既有已資格化欄位在新 trace 沒事件」是不同情況。兩維度不得壓成單一 pass／fail；此區分也不能放寬舊 W1 或歷史 PASS 的契約。

## 4. Slice 總表與建議順序

R 表示所需來源已可支援欄位／契約準備；N 表示數值或規範判定仍需全文；D 表示需相符資料；E 表示需工程師產品定義。這些是開工前提；目前 checkpoint 欄只表示已 review 的限定範圍，不代表完整 slice 資格化。依賴欄只列硬依賴；來源 ID 在每片詳述。

| Slice | 最小交付 | 硬依賴 | 開工前提 | 目前 checkpoint |
| --- | --- | --- | --- | --- |
| S01 | 離線 versioned manifest schema／validator／fixtures／backward compatibility | 無 | R；僅離線 | LOCAL PASS offline |
| P01 | PCIe selection／coverage probe | S01 | R、D | BOUNDED transport |
| P02 | PCIe 原生 LINK／SPLIT 可用性 | P01 | R、D | HOLD |
| P03 | PCIe DLLP／TLP 新增欄位 probe | P01 | R、D | BOUNDED raw fields |
| P04 | PCIe bounded replay 觀測 | P03 | N、D | CANDIDATE |
| P05 | PCIe flow-control accounting | P03 | N、D；須 initial credit 基準 | CANDIDATE |
| P06 | PCIe memory completion coverage | P02, P03 | N、D；只補原生缺口 | CANDIDATE |
| P07 | AER capability 狀態 adapter | S01 | R、N、D | CANDIDATE |
| P08 | DPC capability 狀態 adapter | S01 | N、D | CANDIDATE |
| P09 | ERR／AER／DPC 事件關聯 | P07, P08 | D；承接 G3c | CANDIDATE |
| P10 | ASPM／L1SS observed state | S01 | R、N、D；不作產品政策判定 | BOUNDED LinkControl raw view |
| P11 | Recovery／EQ／reset 觀測 | P01 | R、D；timeout 判定另有 N | BOUNDED valid state points |
| U01 | USB selection／coverage probe | S01 | R、D | BOUNDED transport |
| U02 | USB LINK_CMD 欄位 | U01 | R、D | BOUNDED SSP sample |
| U03 | USB LFPS raw／name mapping | U01 | R、D | BOUNDED raw/name sample |
| U04 | USB LTSSM state 欄名 probe | U01 | D；先取得精確原生欄名 | HOLD blocked_field |
| U05 | USB 原生 transaction／transfer | U01 | R、D；USB2／USB3 分別資格化 | HOLD |
| U06 | USB link／power 觀測規則 | U02, U03 | D；state 規則額外依賴 U04 | CANDIDATE |
| U07 | USB non-stream bulk flow adapter | U05 | R、D | CANDIDATE |
| U08 | USB bounded bulk flow 規則 | U07 | D；先固定一種模式 | CANDIDATE |
| U09 | USB EP0／descriptor adapter | U05 | R、D | CANDIDATE |
| U10 | USB enumeration 最後可證實階段 | U09 | D；USB2／SS 不共用固定序列 | CANDIDATE |
| U11 | USB2 reset／suspend／resume | U01 | D；只在 USB2 trace 適用 | CANDIDATE |
| O01 | 已保存 WHEA／CPER adapter | S01 | D；需要含有效 PCIe section 的記錄 | CANDIDATE |
| O02 | 已保存 USB ETW／usbmon 關聯 | S01 | D；identity／時鐘校準另驗 | CANDIDATE |
| I01 | PCIe 新觀測接既有 W1–W5 report | S01 | 至少一項新 PCIe 輸出已驗證 | BOUNDED P03 source block |
| I02 | USB 新觀測接既有 USB report | S01 | 至少一項新 USB 輸出已驗證 | BOUNDED U02 source block |
| G01 | 一條產品政策 evaluator | P10 | E；Who／When／What／Proof | HOLD engineer input |
| G02 | 一個 vendor register sidecar | S01 | E；完整定義與工具使用權限 | HOLD engineer input |

後續依賴順序仍是 **S01 → U01 → U02／U03／U05**，PCIe 是 **S01 → P01 → P02／P03**。最新授權允許適用的實作／驗證／review 連續執行，不再等待例行逐片確認；箭頭仍不代表資料條件已滿足。U04 找不到 state 欄名時只停 state 分支；不阻擋 LINK_CMD、LFPS 或 EP0。P02 若已充分提供所需 grouping，P06 可縮小或取消。P09 完整 AER＋DPC 關聯以兩個 adapter 為前提；只有 AER 資料時可展示 P07，不為湊合 P09 填造 DPC。

P03、I01／I02、P10／P11 已達各自 bounded checkpoint，見 [欄位驗收](p03-field-checkpoint-20261013.md)、[報告驗收](i01-i02-report-checkpoint-20261013.md)與 [設定／Recovery 觀測](p10-p11-observation-checkpoint-20261013.md)。P04–P09 與 U06–U10 等仍依真實缺口及可用資料選片，不承諾把整張表一次資格化。O01／O02、U11 與 G01／G02 各自等相符輸入；後續報告仍採已驗證一項就接一項。

## 5. PCIe slices

### S01 — 離線 versioned manifest 契約（GO offline）

- **工程師問題／預期觀測**：這份已保存輸入對哪些分析前提有足夠宣告；預期 validator 分開呈現版本／缺值／legacy 處理、欄位能力與事件觀測，且不將宣告升格為 runtime 證明。

- **來源**：LC-01、LC-02、LC-04、LC-05、PCI-06、PCI-09、USB-01、USB-02、USB-03、USB-04。
- **範圍／輸出**：只交付 versioned manifest schema、離線 validator、fixtures 與 backward compatibility；表達來源文件修訂、已讀條款／ECN applicability、capture 模式、selection／eligibility 及缺值語意，具體格式見 [S01 離線契約](s01-offline-contract.md)。本片不 wiring、修改或執行 PCIe／USB 現有 pipeline；實際 manifest 產生與 coverage 整合分別留 P01／U01，不建立共同 protocol core／共同 scoring。
- **驗收**：離線執行 validator 對照完整、缺 mode、缺 epoch、partial capture、unknown filter、field capability 與 event observation 的不同組合及 legacy fixtures；按版本契約區分新格式、可相容舊格式與不支援版本。不同 protocol 的不適用欄位不能自動設假值；既有檔案缺新欄位時保留舊範圍／coverage 未知，不回寫或改變歷史 PASS。Schema／validator 通過只代表契約處理符合預期，不證明真實 trace 內容或 protocol correctness。
- **停止條件／上限**：無法判定 Gen／Flit／role 時，只標記依賴條件未知；不得為取得缺值而啟動 suite／COM／GUI 或 trace probe。W1 frozen、既有 pipeline、兩個 checkout 及已驗證結果維持原範圍；本片不能宣稱 runtime coverage 或協定正確性。

### P01 — PCIe selection／coverage probe

- **工程師問題／預期觀測**：指定 range、filters 與 event levels 是否選入預期資料；預期得到可對帳的分層 counts、effective range 和未覆蓋類型。

- **來源**：LC-01、LC-02、LC-07、LC-13、LC-14、LC-15、LC-16。
- **範圍／輸出**：另行授權後，才把 S01 manifest 契約整合到 PCIe pipeline，並以既有可用 runner 驗 `_PACKET`／相關 `_LINK`／`_SPLIT` 等層級的輸入選取；保存 filters、requested／effective range、counts 與 unsupported level。使用安裝版 named constants。
- **驗收**：Q-P；受控 range、hidden／visible 設定、沒有匹配事件與結束標記的對照；row count 與 packet count 分別對帳。無法觀測 effective range 時明示未知。
- **停止條件／上限**：任何 source／working-copy identity 變動即停止該 run。文件中 API enum 數字不一致不能以猜數字解決；通過只證明指定模式覆蓋。

### P02 — 原生 LINK／SPLIT 可用性與對照

- **工程師問題／預期觀測**：LeCroy 原生 LINK／SPLIT 是否能提供所需完整、失敗或未完成 group；預期看到 status、packet references 與 payload／metrics 的實際可用範圍。

- **來源**：LC-01 §5.2.10–11、LC-13、LC-14；PCI-37 僅作較新版參考。
- **範圍／輸出**：原生 grouped record adapter，保留 TransactionStatus、CompletionStatus、packet references、payload／metrics 與 `vendor_derived` 身分；與既有 G2b／B2 資料對照。
- **驗收**：Q-P；成功、失敗、未完成、多 completion 的適用樣本；確認 packet bounds、單位、status 與 combined payload 是否可取得。沒有實際樣本的情況標未驗證。
- **停止條件／上限**：無 packet references 就不能假裝逐包可追溯；原生 grouping 無法支援需求時留下具體缺口給 P06。對照一致不是獨立 compliance oracle。

### P03 — DLLP／TLP 增量欄位 probe

- **工程師問題／預期觀測**：此版本與 event type 實際提供哪些 replay／credit／completion 欄位；預期以 raw value、單位與有效性對照精確原生 packet。

- **來源**：LC-01 §5.2.2–3、LC-07、LC-15；承接 B1a／G2a。
- **範圍／輸出**：只新增 replay／credit／completion 必需的 PSN、AckNak_SeqNum、VC_ID、HdrFC／DataFC、HdrScale／DataScale、CRC／error、Length／ByteCount／LowerAddr 等適用欄位。逐層適用性表與 raw export。
- **驗收**：Q-P；ACK／NAK、InitFC／UpdateFC、不同 TLP 型別、缺值與不適用欄位；不得在每個 event 都讀所有欄位。已驗證欄位只跑必要回歸。
- **停止條件／上限**：沒有 FC／PSN 事件的 trace 只能完成靜態契約；沒有已驗證欄位不能進對應數值 evaluator。

### P04 — bounded replay 觀測

- **工程師問題／預期觀測**：同一 epoch 的兩向記錄可支持哪些重送／ACK／NAK 對應；預期列出有來源的候選區間及缺口，而不把缺 ACK 當違規。

- **來源**：PCI-06、PCI-09、PCI-13 的適用正文待補；PCI-18 為題目線索，LC-01／07 提供欄位。
- **範圍／輸出**：單一 link epoch、一個發送方向的 sequence／retransmission，以及對向 ACK／NAK 的配對與可追溯候選區間；必須有兩個方向的連續觀測，不能只看單向 TLP。先不加通用 timeout。
- **驗收**：Q-E；正常 ACK、NAK 後重送、sequence wrap、重複 capture row、缺 ACK／截斷、reset 後 sequence 重用；期望值獨立標註。
- **停止條件／上限**：適用序號與重播規則尚未讀到正文，或 coverage 不足時，只輸出 raw sequence／UNKNOWN；不能宣稱 replay error 或 protocol violation。

### P05 — flow-control accounting

- **工程師問題／預期觀測**：具初始基準的指定方向／VC／class 是否能重建公告與消耗序列；預期雙向 FC 對應和未知區段分開，不在缺基準時推餘額。

- **來源**：PCI-06／09 正文 gate；LC-01、PCI-38、PCI-40 為實作參考。
- **範圍／輸出**：先限定一個 VC／發送方向／credit class，把此方向的 TLP 消耗配對對向接收端公告的 FC DLLP；分別保存 announced credit、消耗、更新及初始基準，之後才擴充其他 class。
- **驗收**：Q-E；initial credit、increment／wrap、infinite／scaled credit 的適用案例、missing InitFC、同向 FC 不得誤配、reset、unknown TLP length；不混用 raw count 與縮放後容量。
- **停止條件／上限**：兩向 coverage 必須完整；缺對向 FC，或 capture 沒 InitFC 且沒有可追溯初始基準，就不能推 credit exhaustion／overflow。舊版 LeCroy FC 手冊不保證本機行為。

### P06 — memory completion coverage（條件片）

- **工程師問題／預期觀測**：單一可辨識 outstanding request 的 completion 覆蓋了哪些 bytes；預期列出可證實覆蓋、重疊／缺口及 tag 重用造成的 ambiguous 配對。

- **來源**：PCI-06／09／13 正文 gate；LC-01；PCI-39 僅是 AMD descriptor 說明，不能當 wire layout。
- **範圍／輸出**：P02 明確證明原生結果不足後，才對一種 Memory Read 模式補 request／completion byte coverage；既有 G2b association 只當候選關係，保留 address、BE、length、ByteCount、LowerAddr、status 與 epoch。G2b 的 nearest-preceding RequesterId／Tag 配對不關閉 request，也未證明 tag 重用正確；本片需先證明單一 outstanding request 身分，才算 byte coverage。
- **驗收**：Q-E；多段 completion、partial bytes、重疊／缺口、前筆尚未完成便重用 tag 且 completion 遲到、UR／CA、poison、截斷、零編碼的適用長度語意；不唯一的配對標 ambiguous／UNKNOWN，不分配給最新 request。用獨立 raw fixture，不用 adapter 輸出反推期望。
- **停止條件／上限**：P02 已滿足需求就取消重建工作。規範不足時不能把「未在 window 看到 completion」寫成 timeout；device timeout 設定與觀測起點另須來源。

### P07 — AER capability 狀態 adapter

- **工程師問題／預期觀測**：這個 port／revision 的哪些 AER status、mask、severity 與 header bits 有有效來源；預期並列 raw／validity／讀回，保留未定義與部分有效位元。

- **來源**：PCI-35／36、PCI-44、OS-08、LC-02；精確 register 語意仍以合法取得的適用規範或已核對實作定義為準。
- **範圍／輸出**：沿用 B2c／B2d／B2h 的 capability traversal、partial validity 與原始資料，增加 AER status／mask／severity／header log 的來源化觀測；先限定一種 port type／revision。
- **驗收**：Q-E；未知位元、partial header、截斷 capability chain、錯 port type、write-one-to-clear 意圖與後續讀回分離；COM mask 沿用 B2h2 的逐位元驗證。
- **停止條件／上限**：沒有 offset／bit／revision 的可用定義時只保留 raw capability。沒有讀回不能推已清除；AER mask 也不能反推實際沒有 error。

### P08 — DPC capability 狀態 adapter

- **工程師問題／預期觀測**：是否有有效 DPC capability／trigger／status 可與這次 link 事件並看；預期有資料才顯示 named state，不能只由 link down 推 DPC。

- **來源**：PCI-20、PCI-21、PCI-22、PCI-35／36、PCI-42；摘要不夠支援完整 register 解碼。
- **範圍／輸出**：一種 downstream port 的 DPC capability、trigger／status 與有效位元時間點，使用既有 config access；保留 unsupported／unknown。
- **驗收**：Q-E；DPC 缺席、部分能力有效、trigger／status 有無、clear write 與讀回差異、device／epoch 不同；定義與 fixtures 均須有精確來源。
- **停止條件／上限**：先取得可用定義與相符 capture，才能實作 named fields；link down 本身不能當成 DPC trigger。

### P09 — ERR／AER／DPC 事件關聯

- **工程師問題／預期觀測**：ERR、有效 AER／DPC 記錄與 link transition 是否能對齊同一 device／epoch；預期給出可追溯時間關聯與未連接資料，不輸出根因。

- **來源**：LC-07、PCI-20–22、PCI-23、PCI-32、OS-08；承接 G3c-0／G3c。
- **範圍／輸出**：把 message、有效 status／header log、DPC 與 link transition 放入相同 device／epoch 的可追溯 timeline。只增加關聯證據，不重新做 ERR extractor。
- **驗收**：Q-E；有 ERR 無 status、status 無 message、mask、跨 port、同 BDF 新 epoch、時間精度不足、DPC 無資料；以 packet window／可驗證時鐘各自表示，不混成假精確時間。
- **停止條件／上限**：缺 identity 或時序連接只列並排資料。ERR_COR 也可能是其他訊號用途，不能一律計成硬體故障；輸出是 temporal correlation，不能稱 BSOD root cause。

### P10 — ASPM／L1SS observed state

- **工程師問題／預期觀測**：指定 RC／EP 在此階段的設定意圖、讀回與低功耗觀測是否一致可見；預期分開呈現三者及缺口，不自行定義 Disable ASPM 政策。

- **來源**：PCI-24–27、PCI-45、LC-02；承接 B2g 問卷與 B2h2。
- **範圍／輸出**：先擴一個 standard register 視圖，並列 enable／control 的寫入意圖、讀回、CATC 合併值與已觀測 LTSSM／PM 訊號；RC／EP 分開。
- **驗收**：Q-E；enable 但沒 entry、entry 但 config 未見、只有 write、partial mask、RC 缺資料、相同 BDF 跨 epoch。L1SS 欄位需另有 revision／offset 定義，不由 LinkControl 推算。
- **停止條件／上限**：沒有 CLKREQ#／sideband 證據就不能聲稱已驗證其電氣動作；ASPM enable 不自動表示一定進 idle state。產品 Disable ASPM 是否違反留給 G01。

### P11 — Recovery／EQ／reset 觀測

- **工程師問題／預期觀測**：此 capture 能確認哪些 Recovery／EQ／reset 前後狀態；預期保留 sequence、起訖與缺失方向，不套用未定義 timeout。

- **來源**：LC-16、PCI-18、PCI-29–34；需精確判定時再讀適用 Base／errata／ECN。
- **範圍／輸出**：在現有 LTSSM／speed／width sequence 上標記可見 Recovery、EQ、link-up／down 與 reset 證據，保留原始起訖與觀測缺口。
- **驗收**：Q-E；不同 speed／role、capture 從 Recovery 中途開始、方向缺失、最後狀態截斷、沒有 PERST#、狀態重複；不能用 display milliseconds 補出 nanosecond 門檻。
- **停止條件／上限**：任何 timeout 都要另綁其起點／終點／上限／ECN；這片不清除 B1d 四項驗證債，也不驗證 PHY／EQ 電氣 compliance。

## 6. USB slices

### U01 — USB selection／coverage probe

- **工程師問題／預期觀測**：bad-CRC、未完成 transfer 及所需 event levels 是否被目前選取方式保留；預期以已知樣本對照 flags、range、分層 counts 與覆蓋未知處。

- **來源**：LC-04 p168／170、LC-05、LC-10、LC-11。
- **範圍／輸出**：另行授權後，才把 S01 manifest 契約整合到 USB pipeline；在既有 extractor 模式旁，顯式設定並記錄 bad-CRC、completed／incomplete transfer、event levels、filters 與 range，輸出 coverage manifest。
- **驗收**：Q-P；預設與顯式 flags 的受控對照、已知 bad-CRC 與 incomplete 樣本、counts／結束標記；若現有 trace 沒這類事件，該類覆蓋維持未驗證。
- **停止條件／上限**：僅「run 成功」不能驗覆蓋。新增模式改變 callback 集合時須獨立 qualification，舊 DEMO PASS 的範圍保留。

### U02 — LINK_CMD 欄位

- **工程師問題／預期觀測**：代表性 LINK_CMD 的名稱、raw code 與附屬欄位能否一致取得；預期 packet 級別的對照保留 unknown code 與不適用第二組欄位。

- **來源**：LC-04 §5.2.1.3.6、LC-08、LC-09、LC-12；USB-01 §7.2.4.1.2–3。
- **範圍／輸出**：raw `LnkCmd`／`LinkCmdInfo`／CRC5 與適用的第二組欄位，加上本機 constants 對應的名稱；保留方向、index 與 unknown code。
- **驗收**：Q-P；LGOOD／LBAD／LCRD／LGO 等有樣本才資格化；完整性、CRC、第二組欄位在不適用 mode 不亂填。用精確原生 packet 核對。
- **停止條件／上限**：命令 enum 是 LeCroy 實作值，不能直接拿 USB spec 數字代替；只完成欄位，不判 link 正確性。

### U03 — LFPS raw／name mapping

- **工程師問題／預期觀測**：同一 LFPS event 的 raw type／pattern／duration 與安裝版名稱函式如何對應；預期保留值、單位、origin 與未驗類型，不按 duration 猜意圖。

- **來源**：LC-04 §5.2.1.3.3、LC-09 `GetLfpsDesc`、USB-01 §6.9.1–2。
- **範圍／輸出**：現有 raw LFPS Type／Pattern／duration 對應本機官方名稱函式的結果，同時保留 raw value 與 origin；不由時間長度猜 enum。
- **驗收**：Q-P；raw＋名稱逐項核對、unknown type 保留、pattern 起訖／截斷、duration 單位與精度。沒有樣本的類型不填 verified。
- **停止條件／上限**：Polling／Ping／Reset／Wake 的判定須帶 role／state／Gen 等上下文；只有 raw pattern 不能推 wake／reset 已成功。

### U04 — LTSSM state 欄名與輸出

- **工程師問題／預期觀測**：原生 LTSSM event 的精確 decoded-field label 能否被 API 讀到；預期取得可核對的名稱與 state 值，或明確停在 blocked_field／raw event。

- **來源**：LC-04 p145、p171–174；USB-01 §7.5 為語意來源。
- **範圍／輸出**：先取得 `_USB3_LTSSM_STATE` 真實 packet 的精確 decoded-field 名稱；若 vendor function 可讀才做 state adapter，並列 field name／raw／display。
- **驗收**：Q-P；大小寫、缺欄位、未知 state、不同事件型別不可混讀；至少代表性 transition 有原生顯示對照。
- **停止條件／上限**：手冊只列 event，未證明專用 member。無法取得精確名稱或 runtime 不支持就記 blocked_field，保留 raw event；不猜 `State`，不阻擋 U02／U03／U05。

### U05 — 原生 transaction／transfer 資格化

- **工程師問題／預期觀測**：這份 USB2 或 USB3 trace 的原生 transaction／transfer 能提供哪些 grouping 與狀態；預期 packet bounds、complete／halted、payload 和缺欄位分別可追溯。

- **來源**：LC-04 §5.2.2／5.2.4、LC-10、LC-11。
- **範圍／輸出**：先測 `_TRA`／`_XFER` 的 availability，輸出 native record、packet refs、endpoint／direction、complete／halted 與 payload；USB2、USB3 各有獨立適用矩陣。
- **驗收**：Q-P；completed／incomplete／halted、control／bulk、無 payload／partial payload、First／Last 標記、native group 範圍。手冊 transaction 章含 USB2 PID，不能直接宣稱 USB3 支援全部同名欄位。
- **停止條件／上限**：native grouping 無法滿足的具體欄位才提出 raw packet 補充；本片不寫全新通用 transfer reassembler，也不稱原生 grouping 是獨立真值。

### U06 — link／power 觀測規則

- **工程師問題／預期觀測**：已資格化 command／response 與 state 證據可支持哪一條 link／power 觀測；預期依 role／mode 列出序列與不足條件，不僅憑 LGO 宣稱已進 U state。

- **來源**：USB-01 §6.9／7.2／7.5、USB-05 已閱 TD6.5、TD7.1／13–17／23–29。
- **範圍／輸出**：先選一條有完整輸入的 command／response 觀測，再擴 U1／U2／U3／Recovery；state-specific 規則必須另完成 U04，否則只呈現 command 序列。
- **驗收**：Q-E；正常、reject／retry、缺 response、方向錯誤、capture 截斷、不同 Gen／lane／role、retimer 適用性。測試規範中的 exerciser 刺激不能當被動 trace 已滿足。
- **停止條件／上限**：定時條件缺解析度／狀態就 UNKNOWN；沒有 LTSSM 證據不能因 LGO 出現就宣稱已進 U state；不產生 USB-IF certification 結論。

### U07 — non-stream bulk flow adapter

- **工程師問題／預期觀測**：指定 non-stream bulk endpoint／direction 的資料和 flow-control packet 能否對齊；預期 raw packet 與 native group 相互引用，未知與 partial burst 不被吞掉。

- **來源**：USB-01 §8.5.2–3／8.10.1–3、LC-04，承接 U05。
- **範圍／輸出**：先限定一種 SS non-stream bulk 方向，把 DP／ACK／NRDY／ERDY 與 native transfer 對齊；保留 endpoint、sequence／NumP／EOB 等實際可取得欄位。缺欄位先做增量 probe，不能合成。
- **驗收**：Q-P／Q-E；data／retry、相同 endpoint 相反方向、reset 後位址重用、缺 ACK、partial burst；raw 包和 native group 相互引用且不吞未知包。
- **停止條件／上限**：control、isochronous、streams 與多 endpoint 排程先排除；輸出 flow evidence，尚不判定 host／device 違規。

### U08 — bounded bulk flow 規則

- **工程師問題／預期觀測**：在已固定模式下，資料是否符合已讀的一條 flow-control／sequence 不變量；預期允許規範准許的未等 ERDY 再送交易情境，並保留無法判定窗口。

- **來源**：USB-01 §8.10.1–3，新增規則前逐條確認 §8.5 等精確正文及適用 ECN。
- **範圍／輸出**：針對 U07 那一種模式，先實作一條 flow-control／sequence 不變量及證據窗口；state-machine 只處理已定義模式。
- **驗收**：Q-E；正常 NRDY→ERDY、host 在未收到 ERDY 前再送 transaction、重複／遲到 ERDY、retry、截斷、endpoint／direction 不符與 sequence wrap。
- **停止條件／上限**：USB3.2 §8.10.1 允許 host 在 flow-control 回覆後、不等 ERDY 就恢復 transaction；不能做「NRDY 後沒有 ERDY＝違規」規則。streams 等例外未處理前不可擴用。

### U09 — EP0／descriptor adapter

- **工程師問題／預期觀測**：EP0 request、data、status 及 descriptor bytes 中哪些有完整來源；預期列出成功／STALL／截斷與未知 descriptor，不以補零形成有效 payload。

- **來源**：LC-04 control transfer fields、USB-01 §9.4／9.6、USB-08；USB2 分支使用 USB-03／10 的適用正文。
- **範圍／輸出**：在原生 control transfer 上取 request type／recipient／direction、bRequest／wValue／wIndex／wLength、data／status 與實際 descriptor bytes。先處理 device／configuration／BOS 的有界 payload，不一次覆蓋所有 class。
- **驗收**：Q-E；short／truncated descriptor、length 不一致、STALL、沒有 status、unknown descriptor、少於請求長度與超過輸入邊界；保存 raw bytes，不能補 0 形成假 descriptor。
- **停止條件／上限**：payload／status 沒資格化就只列 request。新增 descriptor 的 layout 必須先讀對應章節；class-specific 與 hub 分支另排條件工作。

### U10 — enumeration 最後可證實階段

- **工程師問題／預期觀測**：這次 enumeration 最後能由成功 control stage 證實到哪一步；預期分 USB2／SS profile 呈現已確認階段與 capture 缺口，不強加固定 host 序列。

- **來源**：USB-01 §9.1.2／9.4.6–7、USB-03 §9.1.2、USB-08、USB-12。
- **範圍／輸出**：分 USB2／SS profile 顯示 reset／address／descriptor／configuration 等已確認事件和最後成功 control stage；不是強制所有 host 採同一順序。
- **驗收**：Q-E；SET_ADDRESS 有 request 無成功 status、成功後 address 變更、重試、STALL、reset／新 epoch、只抓到後半段、SS 的 SET_SEL／IsochDelay 適用情境；未出現的可選步驟不自動 fail。
- **停止條件／上限**：缺 status 或 capture 末端只能說最後可證實階段；USB2／SS fallback／同實體 connector 關聯需要兩邊 port 證據，不能由單邊 log 推出。

### U11 — USB2 reset／suspend／resume（條件片）

- **工程師問題／預期觀測**：確定速度的 USB2 trace 能觀測哪些 reset／suspend／resume 起訖；預期區分 host resume、remote wake 與缺少時序證據，不推電氣結果。

- **來源**：USB-03 §7.1.7.5–7、USB-04 適用 ECN 待逐條查；USB-10／14 為測試範圍參考。
- **範圍／輸出**：只在確定 LS／FS／HS 與對應事件可取得的 USB2 trace 上做一個 reset／resume observation profile。
- **驗收**：Q-P／Q-E；速度差異、remote wake／host resume、起訖不全、時間精度不足、LPM 不適用；先驗欄位再做定時規則。
- **停止條件／上限**：不套在 `_USB3_*` 事件上；decoded packets 不能證明電壓、rise time 或 electrical compliance。

## 7. OS 關聯、報告與等待工程師的 slices

### O01 — 已保存 WHEA／CPER 記錄

- **工程師問題／預期觀測**：已保存錯誤記錄是否含有效且版本相符的 PCIe section；預期保留 ValidBits、AER bytes、device identity 與時間有效性，不由 0x124 單獨判根因。

- **來源**：OS-01、OS-02、OS-03、OS-04、PCI-43。
- **範圍／輸出**：唯讀解析已保存記錄；保留 error source、record／section revision、length、ValidBits、BDF、AER bytes 及時間來源。先做一種可驗證格式，不啟動 live collection。
- **驗收**：Q-E；0x124 非 PCIe source、缺 PCIe section、invalid field、截斷、不同 revision、timestamp 精度／有效性；未識別 section 原樣保留。
- **停止條件／上限**：沒有合適記錄就只完成契約。CPER 記錄時間不保證是錯誤發生時間；dump／trace 同 BDF 仍需 device epoch／clock 證據，不能直接判因果。

### O02 — 已保存 USB ETW／usbmon 關聯

- **工程師問題／預期觀測**：已保存 host request 與 wire trace 是否有足夠 identity／clock 證據可關聯；預期呈現可校準的配對與不確定度，否則只並排。

- **來源**：OS-05、OS-06、OS-07。
- **範圍／輸出**：先選 ETW 或 usbmon 一種已保存輸入，按 provider／activity／device／endpoint 建索引；與 wire trace 的關聯結果附 clock offset／不確定度，無校準時僅並排。
- **驗收**：Q-E；URB submit／complete 差異、重用 ID、missing／dropped event、payload 截斷、address 重用、clock drift／reset；host request 不能被計成 wire packet。
- **停止條件／上限**：不安裝 driver、不啟用追蹤、不收集 live log；Activity ID 不是時間校準，usbmon 也不是 LFPS／LTSSM 真值。

### I01 — PCIe 新觀測接既有 W1–W5 report

- **工程師問題／預期觀測**：新 PCIe 觀測能否在報告中保持其來源、型別與 UNKNOWN 邊界；預期 JSON／MD／HTML 語意一致且不透過 opaque extension 繞過 W1 frozen contract。

- **來源**：新增觀測各自的 source IDs；現有 W1–W5 contract／timeline／report 為實作基礎。
- **範圍／輸出**：一次只接一項已驗證 PCIe slice，保存 input hash、rule source／version、packet refs、validity、vendor-derived 與 observed／inferred 區別。先定義具型別的 protocol-check 輸出或獨立來源區塊，再做 renderer；不重新設計整個報告。
- **驗收**：來源引用可解析、JSON→MD／HTML 語意一致、unknown 不被渲染成 pass、非完整 capture 不隱藏、缺必要欄位明示；新增 typed 欄位／validator 與現有 report harness 一起驗證。負面案例必須拒絕把 opaque extension 當已驗證事實。
- **停止條件／上限**：W1 v1 固定 `effective/expected=UNKNOWN`、`policy=NOT_EVALUATED`；`extensions/details` 的其他文字是 opaque provenance。不能把新 verdict 塞入它們繞過 frozen contract。產品政策 G01 的未來 typed 輸出需獨立契約，不放寬 W1。兩 checkout 所需 dependencies 未清楚定位就不搬檔；報告呈現不提高上游證據強度，不與 USB 共用判定 core。

### I02 — USB 新觀測接既有 USB report

- **工程師問題／預期觀測**：USB 新觀測進入既有報告後是否保留 coverage 與 raw／native origin；預期 unknown、候選窗口與歷史比較各有來源，不被渲染成根因。

- **來源**：LC-04／05 及該 USB slice 規範來源；既有 DEMO／C 系列 report 為基礎。
- **範圍／輸出**：沿既有 C5 JSON→HTML 一次接一項 command／transfer／enumeration 觀測；並列 selection coverage、raw／native origin、source version 與 missing prerequisites，保留歷史評分與新協定觀察的各自來源。
- **驗收**：對照正負 fixture 的 JSON／呈現結果，確認 absent／unknown 與 candidate window 不被改成 root cause；原有比較與 source-integrity 資訊保留。
- **停止條件／上限**：不建立跨協定共同 scoring／通用 root-cause engine；只有 schema 相似不構成共用語意證據。

### G01 — 一條產品政策 evaluator（等工程師）

- **工程師問題／預期觀測**：工程師指定的 Who／When／What／Proof 是否足以判定一條產品政策；預期僅在完整 scope 與所需證據下輸出該政策結果，缺條件仍保持觀測。

- **來源**：[B2g 問卷](pcie-b2g-engineer-questions.md)、適用 standard register 定義；工程師回覆另外保存來源身分。
- **範圍／輸出**：先選一個 device／epoch／phase／register 規則；Who（RC／EP、BDF）、When、What（bits／expected）、Proof（write intent 或讀回）完整才轉成可執行條件。
- **驗收**：符合、違反、缺 scope、只有 write 無 required readback、時間窗口不符；每個結果有 packet／source refs。
- **停止條件／上限**：沒有完整回覆就保持觀測，不從檔名「Disable ASPM」推全系統 expected state；研究發現不替工程師決定產品政策。

### G02 — 一個 vendor register sidecar（等工程師）

- **工程師問題／預期觀測**：所提供 vendor register 定義是否足以解讀特定 device／revision 的有效位元；預期以獨立 known example 對照 sidecar，未定義與未知 bit 保留。

- **來源**：[vendor register 需求](pcie-vendor-register-request.md)、[B2h2](pcie-b2h2-sidecar-evidence.md)，後續加入有工具使用權限的 vendor 定義。
- **範圍／輸出**：沿用 `.regdef.json` 與 sidecar，先加一個有 known example 的 register；需 address space、device／revision、offset、width／bits、access／write semantics、來源及使用權限。
- **驗收**：獨立已知值、部分有效位元、錯 revision／device、跨界、write／readback／CATC 合併值分離；不因有名字就把 unknown bit 補成 0。
- **停止條件／上限**：`0x940[1]` 這種片段不足以定義 register。MMIO、`.pecfgdec`、`BuildConfigurationSpace` 與安裝目錄修改維持原先排除範圍。

## 8. 已找到但不納入目前主線的分支

| 家族／來源 | 開啟條件 | 目前界線 |
| --- | --- | --- |
| PCIe Flit／6.x／7.x（PCI-10／11／15–17） | 真實 Flit capture、設備能力、適用版本需求 | 不把最新版本規則倒套目前 non-Flit 資料 |
| CEM／M.2／sideband／firmware（PCI-22／27–34／47／49／50） | 具體 form factor、PERST#／CLKREQ#／平台事件與產品問題 | 目錄／摘要線索不能變成 trace 已有 pin-level 證據 |
| PHY／electrical／正式 certification（PCI-14／17／48、USB-13–16） | 測試設備、fixture、程序全文與明確測試範圍 | 不下載執行測試工具、不以被動 log 代替完整測試 |
| USB hub（USB-06／09） | hub／compound device topology 與 port status 資料 | Hub LVS 與 Hub CV 為不同規範；未讀規則先不實作 |
| USB4／Type-C／PD（USB-17–19） | router／tunnel、CC／PD capture 與具體需求 | 接頭外形不能證明 USB4／PD；目前僅入口盤點 |
| xHCI（USB-11／20） | controller revision、TRB／ring／register 證據 | host interface 與 wire protocol 分層；不先建 ring parser |
| BOT／UAS、其他 class（USB-21–25、USB-07 包內文件） | descriptor／class／transport 已確認且有相符 transfer | Bootability／CTS 不等於完整 UAS 標準；不假定裝置一定使用 BOT 或 UAS |

這些分支有 source IDs 與入口，未切成承諾實作的工作。只有相符需求／資料出現才另切最小 slice，避免先建無法驗證的完整 protocol stack。

## 9. 本輪交付與執行界線

來源登錄、閱讀範圍、既有能力對照及 29 片依賴／驗收／停止條件已保留。本次授權只把 S01 推進離線實作；schema、validator、fixtures 與 backward compatibility 的完成證據另見 [S01 離線契約](s01-offline-contract.md)，本計畫本身不構成測試通過。LeCroy／COM／GUI、硬體、trace／coverage probe 與其餘 28 片仍不在本輪執行範圍；W1 frozen，不搬 checkout。

S01 已完成並經 review；依最新指示接 U01／P01，之後在各自前置驗證範圍內逐片實作、驗證與 review，不逐片重問執行授權。G01／G02 仍等待工程師完整產品定義，其他候選保留各自來源與資料門檻。本節前段的「本次授權只把 S01」描述原第一輪審查的歷史範圍，最新授權以上表為準。
