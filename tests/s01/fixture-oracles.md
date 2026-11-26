# S01 fixture oracles

日期：2026-10-13。這份文件先於本輪測試程式建立，固定獨立的預期語意，再依 root 公開的 schema／API 契約對映。`test_s01_contract.py` 的 42 個離線測試方法已執行通過，包含 8 份 manifest × 8 個 profile 的 64 組手寫預期；不表示任何 trace 或 extractor 通過 qualification。期望值不從 production function 反算。

本輪只處理 versioned manifest、validator、合成 fixtures、backward compatibility 與輸入 readiness。沒有 protocol evaluator、pipeline 重構、LeCroy／COM／VSE／GUI、trace 重播、硬體、checkout 搬檔或交付操作。

## 獨立依據

| Oracle ID | 來源與已知範圍 | 本文件採用的不變量 |
| --- | --- | --- |
| O-USER | 本輪使用者的 8 項要求；由 root 轉述並限定本輪 offline S01 | 狀態分軸；legacy 不猜 metadata；歷史 PASS 保留原 scope；W1–W5 frozen；至少七類基本 fixture；期望不能複製 production logic；保留兩個 checkout |
| O-S01 | [slice 計畫 §5 S01](../../docs/pcie-usb-spec-slices-20261013.md) | 缺 mode／epoch／coverage 僅阻擋依賴它們的工作；不適用欄位不補假值；readiness 不等於 runtime 或協定正確性 |
| O-QP | [slice 計畫 §3 Q-P](../../docs/pcie-usb-spec-slices-20261013.md#3-各片共用的驗收規則) | 保存 identity、版本、方向、epoch、requested/effective range、filters、selection、capture 與 extraction 範圍；row／callback／packet 不互當分母；文件存在不等於 runtime 可用 |
| O-QE | 同文件 §3 Q-E | unknown 不當 0，not observed 不當 absent；缺資料與截斷有明確處理；來源未讀正文不能生出 strict PASS／FAIL |
| O-LC-PCI | [來源地圖](../../docs/pcie-usb-source-map-20261013.md)，LC-02：安裝版 13.26 Automation Manual，ExportToText PDF366–367 | 匯出受 display-hidden packets 與有效 range 影響；只知道 API 成功不足以支援缺事件主張 |
| O-LC-USB | 同地圖 LC-04：USB VSE manual v9.12／Suite 10.13+，SendTransfer PDF168、badCRC PDF170；LC-05 ExportToText PDF112–113 | completed-only 與 bad-CRC selection 會改變輸入集合；事件未出現在輸出不等於不存在於 capture |
| O-VERSION | 同地圖版本界線與來源登錄；PCI-06／09、USB-01–04、LC-01／04、PCI-37 | 文件版本、bundle 日期、安裝版本和已讀深度分開；non-Flit 不承接 Flit 規則；未知適用版本保持未知 |
| O-NO-VERDICT | [slice 計畫 I01](../../docs/pcie-usb-spec-slices-20261013.md#i01--pcie-新觀測接既有-w1w5-report) 與 O-USER | manifest／extension／readiness 不新增 typed verdict，不把敘述文字升格成 qualification、compliance 或 root-cause 結果 |

上列協定來源只支持選取、適用性與證據界線；本文件不聲稱取得 PCIe Base／errata 會員全文，也不自行定義 protocol timing／credit／completion 門檻。狀態列舉和負面觀察必要条件是本輪 S01 契約，不冒稱 PCI-SIG／USB-IF 的規範措辭。

## 語意與判定層次

Capability 狀態分三軸保存：

- `api_support`: `supported` / `unsupported` / `unknown`。
- `applicability`: `applicable` / `not_applicable` / `unknown`。
- `availability`: `available` / `unavailable` / `unknown` / `not_applicable`。

事件觀察另有 `observed` / `not_observed_in_coverage` / `unknown` / `not_applicable`。可用的 API 沒遇到事件仍可 `supported`；欄位不可用不能把事件改成不存在。任何互斥檢查都必須限定同一 capability／取得途徑／scope，不能拿不同途徑的結果互相否定。

三種不同結果不可合併：

1. **Manifest 有效性**：結構、狀態與引用是否自洽。合法的 unknown 是有效 metadata，不因不完整就一律變成 malformed input。
2. **Profile readiness**：指定 profile 的輸入前提是否都有 metadata 聲明。profile 必須明列 protocol、modes 與非空 requirements；缺條件須附原因，只阻擋相關 profile。欄位／事件的 `not_applicable` 保留在 condition，彙總不得為 eligible，也不能當協定失敗。S01 驗 metadata 的自洽，不認證引用內容的真實性。
3. **Qualification／判定**：不由 S01 產生。readiness 全滿足也沒有授權 runtime，更不能表示欄位、規則或裝置已 verified。

`not_observed_in_coverage` 必須同時具有已知 selected、retained、extraction complete、known filter 和 bounded effective range，且沒有該 scope 內事件證據。未知 filter、只知 requested range、只有 callback count 或 extractor success 都不能替代這些前提。`0` 必須是對明確分母及範圍得到的觀測值，不能由 null、缺 key、空字串或 unknown 轉換。

Capture 是否涵蓋整個情境與 extractor 是否遍歷完選定範圍不同。Partial capture 可阻擋需要完整情境的 profile；若一個較窄的 effective window 有完整負面觀察前提，仍可陳述該 window 的未觀察結果，不能擴張成整段 capture 或 reset 前後的結論。相反地，可靠的正向事件可在 partial capture 中保留 `observed`。

## 合成基準與 profile

Fixtures 使用人工指定的小型 metadata，不含 trace binaries 或虛構的真實 qualification。基準 B 的來源 ID、hash 與 refs 使用 fixture 專用名稱；hash 格式合格不代表某個真實檔案已存在或已核驗。每份 manifest 內有最小 `sources`／`evidence` 表，測試執行時不上網。

基準 B 為 `complete-pcie.json`，包含 schema version、manifest／trace identity、protocol／mode、epoch、toolchain、三軸 capability 狀態、observations 的 selection／retention／extraction／start_index／end_index、filters 與可解析的 evidence refs。ACK 正例是 count=1 的手寫 aggregate observation；NAK 負例是 count=0 且五個前提均成立的 observation。v1 沒有獨立 working-copy、requested-range 或 packet-reference 欄位；不能宣稱已保存或驗證這些額外證據。

`profiles.json` 有 8 個手寫 profile。R-MODE／R-BIDIRECTIONAL 要求雙向資料；R-EPOCH 要求 epoch known；R-FULL 要求 capture_start／capture_end 的 value 明確為 complete；R-WINDOW 要求 NAK coverage complete 且 not_observed_in_coverage；R-FIELD 要求 AckNak_SeqNum available；R-POSITIVE 要求 ACK observed；R-USB 要求 USB3-SS mode、LnkCmd available 與 LINK_CMD observed。

所有 profile 另有 root 指定的三個共通條件 `trace.sha256`、`trace.protocol`、`fact:mode`。因此 missing-mode fixture 對所有本輪 profiles 都不 eligible；這是所有 profiles 明列 mode 的契約決定，不能為了局部性測試省略該前提。epoch 則只有 R-EPOCH 依賴。彙總固定為全部 met＝eligible；部分 met＝partial；零 met 且有 missing／not_applicable＝missing；零 met 且全 unknown＝unknown。每個 assessment 的 qualification 固定 NOT_EVALUATED。

## 必要案例

| Case ID | 手工輸入與變化 | 獨立預期結果 | Oracle |
| --- | --- | --- | --- |
| S01-C01 complete | B，與所有 profile 前提的證據相符 | manifest valid；適用 profiles ready；事件 observed；無 qualification／compliance／root-cause verdict | O-USER、O-S01、O-NO-VERDICT |
| S01-C02 missing-mode | B 的 mode 改為 state unknown、value null；另刪除 mode key | unknown 是 valid；所有本輪 profile 因明列 modes 而 partial；刪 key 是 malformed input；既有正向事件保留 | O-S01、O-QE |
| S01-C03 missing-epoch | epoch unknown／legacy 缺省 | R-EPOCH 不 ready；不能按相同 BDF 偷補 epoch；不改寫事件正向證據或獨立 R-MODE readiness | O-S01、O-QP |
| S01-C04 partial-capture | capture 明示 partial，extraction 在有效範圍完成 | R-FULL 不 ready；正向 observed 保留；R-WINDOW 僅在其五個前提全滿足時 ready；不得形成全情境 absent 結論 | O-S01、O-QP、O-QE |
| S01-C05 unknown-filter | filter unknown；NAK 改 unknown/count null，另測硬留負面觀察 | manifest 可承載 unknown；R-WINDOW partial；硬留 not_observed_in_coverage 必須拒絕；R-POSITIVE 仍 eligible | O-LC-PCI、O-LC-USB、O-QE |
| S01-C06 legacy | 最小舊版輸入含已知歷史 PASS／舊 scope，但無新 metadata | 顯式標 legacy 或缺新 metadata；coverage unknown；不猜 mode／filters／epoch；歷史結果與其 scope 原樣保留；不產生新 qualification | O-USER、O-S01 |
| S01-C07 inapplicable | USB2-HS manifest 內 PCIe 專有欄位／事件標 not_applicable | valid；field/event condition 保留 not_applicable；彙總因已知 identity 等條件是 partial，不能 eligible 或協定 fail；不以 0／false 代替 NA | O-USER、O-S01 |
| S01-N01 absence-supported | B0，五個負面觀察前提均已知且成立 | 可陳述指定 effective window 的 not_observed_in_coverage；capability supported 不因零事件改 unsupported；不能稱 absent／protocol PASS | O-QP、O-QE、O-NO-VERDICT |
| S01-N02 absence-prerequisite | B0 分別改 selected、retained、extraction-complete、known-filter 任一項為 unknown 或不成立 | 每個單因素變化都阻止負面觀察；如果輸入硬宣稱 not_observed_in_coverage，validator 必須拒絕矛盾；不能只改成 false/0 後接受 | O-USER、O-LC-PCI、O-LC-USB |
| S01-N03 missing-bounds | 負面觀察的 start_index 或 end_index 為 null | validator 拒絕負面觀察；v1 不接受 requested-range 當替代欄位 | O-QP、O-LC-PCI |
| S01-N04 count-evidence | unknown/null count；另給 observed＋count 0、not_observed＋正整數、負數、非整數、boolean 假扮 count | unknown 不轉零；同 scope 明確互相衝突或非法 count 必須拒絕；row／packet／callback count 不互相補值 | O-QP、O-QE |
| S01-N05 positive-with-gaps | 一筆可靠正向事件，但未知 filter 或 partial capture | 事件仍 observed；負面推論/readiness 依前提受限；不得因整體 coverage 未知就丟失該事件 | O-QE |
| S01-N06 bounds | ordered bounds；相同 start=end；反向 bounds；boolean bounds | 相同 start=end 是合法 bounded metadata；反向／boolean 必須拒絕。v1 沒有 index namespace 欄位，不聲稱驗證跨 namespace identity | O-QP |
| S01-A01 unsupported | api_support unsupported，applicability applicable，availability unavailable；事件 unknown | 合法可表達的限制；需要該 capability 的 profile 不 ready；事件不自動 not_observed／not_applicable | O-USER |
| S01-A02 api-unknown | api_support unknown；文件只說其他版本支援，沒有本版證據 | 不得補 supported；只擋依賴該 API 的 profile；保留文件與安裝版差異 | O-USER、O-VERSION |
| S01-A03 applicable-unavailable | api_support supported、applicable、unavailable（已知這份輸出未提供該欄位） | supported 與 unavailable 可同時成立；availability 不代替事件觀察；profile 回報缺資料而非 API 不支援 | O-USER、O-QP |
| S01-A04 not-applicable | api_support 可為 supported，但 applicability not_applicable、availability not_applicable、事件 not_applicable | 分軸合法；不必把 SDK 整體 support 改 unsupported；該 profile 不適用而非資格化通過 | O-USER |
| S01-A05 contradictions | 同一 capability/scope 宣稱 not_applicable＋available；或 applicable＋availability not_applicable；同一事件 observed 與 not_applicable | 必須拒絕自相矛盾的 metadata，不能用欄位優先順序靜默選一個；不同 route 則分開紀錄再評估 | O-USER、O-QE |
| S01-A06 empty-profile | requirements 空；modes 空；未知 fact id；錯 expected token | evaluate_profile 拋 ContractError；不得以 all([]) 自動 eligible | O-S01、O-NO-VERDICT |
| S01-V01 schema-version | 明示支援版本；未知 future major；非法型別；沒有 version 的 legacy | 支援版按契約解析；future/非法版明確拒絕，不默認 current；legacy 走明示兼容分支且 coverage unknown | O-USER、O-VERSION |
| S01-V02 document-version | public 13.40 文件＋安裝 13.26；USB manual 與 executable 版本不同；bundle日期不同於base版次 | 原值保留；不拼成單一latest；不能因此宣稱本機field support或新protocol scope已驗證 | O-VERSION、O-QP |
| S01-V03 protocol/mode applicability | PCIe／non-Flit manifest 對 USB3-SS profile；mode unknown；mode已知不符 | 隱含protocol／mode conditions 明示 mismatch或unknown，不能eligible；不解析背景文件去猜實際mode | O-VERSION、O-S01 |
| S01-R01 refs-resolve | identity、fact、toolchain、source、capability、event、history各放懸空ref；另驗重複各類ID | validator 拒絕；不能拿任意現存entry頂替；只驗本地 metadata 引用關係，不是來源真實性認證 | O-QP、O-QE |
| S01-R02 matrix-consistency | matrix竄改status、condition、ref、slice id或刪除assessment；嵌入invalid manifest | validate_matrix拒絕，避免曾經eligible的標籤脫離目前manifest/profile仍被沿用；不聲稱檢查ref指向外部內容的真實scope | O-QP、O-QE |
| S01-R03 source-depth preservation | metadata-only來源＋文件13.40／工具13.26 | valid且原值保留；qualification仍NOT_EVALUATED；v1不具normative-rule profile，不聲稱自動核驗來源深度是否足以支撐協定規則 | O-QE、O-VERSION |
| S01-R04 hidden-verdict | root／trace／capability／event注入verified；matrix qualification改PASS；另有historical_claims | 非契約欄位與新qualification拒絕；歷史claim/scope/ref保存且不影響readiness | O-USER、O-NO-VERDICT |
| S01-R05 empty-evidence | 已知identity、fact、toolchain、capability、event、history的refs清空 | validator拒絕；不能僅因value已填就算已證實前提 | O-QP、O-QE |
| S01-R06 evidence binding | recorded／legacy 的knownfacts、available欄位或事件使用document-only、缺trace_sha256或wrong-trace refs；另用matching saved_output/manual_review/legacy正例 | document不能當trace觀察；matching正例valid，其餘拒絕。API supported的document ref需對到applicable且sections_reviewed的source；metadata-only、NA、unknown applicability或不匹配來源拒絕。synthetic只驗合成聲明，不認證真實trace | O-QP、O-QE、O-VERSION |
| S01-R07 finite JSON | 合法JSON數字1e400放入legacy輸入 | legacy_view拋ContractError；CLI exit 2並有JSON診斷，不能因Infinity序列化拋未捕捉例外；輸入bytes不變 | O-USER、O-QE |

## 需觀察的行為與回歸界線

- 測試應呼叫實際 S01 validator／readiness API，檢查輸出的狀態、原因與引用；不得只驗 mock call count 或 schema 檔存在。
- 同一 fixture 重跑結果具決定性；validator 不原地修改輸入；source/evidence refs、unknown 與歷史結果經 round-trip 不丟失。若有檔案CLI，另外驗證輸入bytes不變及既有輸出不被覆寫。
- 單因素 fixture 直接由手寫基準的指定欄位改動，預期結果固定在測試；不能 import production constants／predicates 來生成期望狀態，不能讓被測validator產生自己的golden。
- Readiness 的局部性以profile已明列前提為準：epoch未知只使R-EPOCH受限，不能使R-POSITIVE跟著失敗；mode是所有本輪profile的共通前提。增加無關背景來源不能讓缺epoch的profile變eligible。
- API 對映只採root提供的契約，沒有閱讀production函式來生成期望。首輪matrix測試因衍生fixtures重用trace_id被unique-ID gate拒絕；修為每份合成fixture独立身分，沒有改production或改readiness期望。
- 後續測試僅證明這組 manifest/validator 的行為；沒有真實事件的合成fixture不能資格化欄位，也不能重開或擴大 DEMO、B1/B2、G2/G3 與 W1–W5 的歷史 PASS。

## 實際檔案與驗證

- Schema：`schemas/s01-input-manifest-v1.schema.json`、`schemas/s01-trace-eligibility-v1.schema.json`。測試只引用公開API，不import production constants產生期望。
- API：`validate_manifest`／`validate_matrix` 回傳 code/path/message errors；`evaluate_profile`／`build_matrix` 回傳input readiness；非法輸入拋ContractError；`legacy_view`唯讀保留original並將coverage標unknown。
- Fixtures：8份manifest、profiles、手寫expected-readiness，以及PCIe／USB兩份synthetic legacy，共12份JSON。USB legacy採現有`run-demo.ps1`的`working_copy`單數結構，未複製untracked真實輸出。
- 命令：`python -X utf8 -B -m unittest discover -s tests/s01 -p test_s01_contract.py -v`；42 tests通過。CLI subprocess只呼叫離線S01命令，驗證stdout JSON、invalid exit 2、輸入bytes及temp目錄不被改寫。
- 範圍限制：v1驗結構、聲明一致性、內部refs、evidence kind／trace_sha256綁定與profile對應；不打開evidence locator、raw trace或來源網站，不認證metadata內容是否真實，不新增runtime／protocol qualification。
