# S01 離線輸入契約與驗收

本輪依 2026-10-13 的 **APPROVE WITH CHANGES** 實作，僅限 schema、validator、fixtures、相容性檢視與 eligibility 資料契約。既有 PCIe／USB extraction、scoring、report 及 W1–W5 frozen contract 均未接入或改動。其餘 28 片未取得執行授權；本地驗收後停止，不啟動 U01／P01。

工程師要回答的是「這份資料能支援哪一項觀測，哪些條件還不知道」，而不是由 metadata 推出根因。29 片的工程師問題／預期觀測與授權狀態見 [slice 計畫](pcie-usb-spec-slices-20261013.md)。來源與選取預設依據見 [來源地圖](pcie-usb-source-map-20261013.md) 及 [來源登錄](pcie-usb-source-register-20261013.json)。

## 檔案與執行入口

| 檔案 | 用途 |
| --- | --- |
| [input schema](../schemas/s01-input-manifest-v1.schema.json) | `s01.input-manifest/v1`，只描述輸入、能力、觀測與來源 |
| [eligibility schema](../schemas/s01-trace-eligibility-v1.schema.json) | `s01.trace-eligibility/v1`，每份 trace 對每個 profile 的條件矩陣 |
| [standalone validator](../tools/s01_contract.py) | Python standard library，結構及跨欄位檢查、eligibility 重算、legacy 檢視 |
| [獨立 fixture 依據](../tests/s01/fixture-oracles.md) | 每個案例的預期與要求來源；不以 production 計算結果產生期望 |
| [測試](../tests/s01/test_s01_contract.py) | 實際呼叫 validator、matrix evaluator、legacy reader 與 CLI |

執行範例（在 repo root，使用可用的 Python 3）：

```text
python -X utf8 -B -m unittest discover -s tests/s01 -p "test_*.py" -v
python -X utf8 -B tools/s01_contract.py manifest <manifest.json>
python -X utf8 -B tools/s01_contract.py matrix <eligibility.json>
python -X utf8 -B tools/s01_contract.py legacy samples/pcie/triage-input-hang-p4a.json --legacy-format pcie.triage-input/v1
```

CLI 僅讀明確指定的 JSON，輸出到 stdout；不追蹤 JSON 內任何 evidence／trace／executable path，不寫輸入，不開網路、不 import 既有 pipeline。有效輸入退出碼 0；無效輸入、未知版本、重複 JSON key、非有限／溢位數字與格式錯誤退出碼 2。`valid` 只表示 metadata 一致性通過，並固定 `qualification=NOT_EVALUATED`。

JSON Schema 使用 Draft 2020-12 可表達的結構詞彙；離線 walker 只實作本專案兩份 schema 實際使用的有限詞彙，並拒絕其他 schema keyword／reference，不是通用 JSON Schema library。跨欄位關係須用本 validator 驗證；只通過第三方的結構 schema 不代表通過 S01 語意檢查。

## 1. 輸入 manifest

所有定義的欄位都必須存在，未宣告的欄位拒絕。缺 mode／epoch 的意思應表示成 `state=unknown, value=null`；直接漏 key 是格式錯誤，不能默默補值。對 legacy 缺欄位則走下節的顯式相容性入口。

| 區塊 | 內容與界線 |
| --- | --- |
| `manifest_id`, `origin` | 記錄身分；synthetic／recorded／legacy 分開。Synthetic evidence 不能標成 recorded |
| `trace` | Trace ID、宣告的 trace SHA-256（可 null）、協定及 identity evidence refs；這不是輸入 JSON 檔本身的 hash |
| `trace.facts` | mode、bidirectional、capture_start、capture_end、epoch、filters；每項有 state、value、evidence refs |
| `toolchain` | software version、extractor／constants SHA-256 與 refs；缺資料為 null，不從本機目前版本補回歷史 run |
| `sources` | source ID、revision、locator、read depth、sections、applicability、evidence refs；選讀必須列出章節 |
| `evidence` | 可解析的本文件內 evidence IDs、locator、來源檔 hash（可 null）、kind、note；觀測證據另以 `trace_sha256` 綁定 trace；locator 只當資料，不自動讀取 |
| `capabilities` | 每個 API／欄位的三個獨立維度，見下表 |
| `observations` | 每種事件的觀測狀態、實際輸出 count 及 bounded coverage |
| `historical_claims` | 歷史 claim 名稱、原 scope 與 refs；不重新評分或擴張原 PASS |
| `claim_boundary` | 固定 `INPUT_METADATA_ONLY`，沒有 compliance／root-cause verdict 欄位 |

`known` fact 必須有合型別的值及 evidence refs；`unknown` 與 `not_applicable` 的值都必須是 null，但兩個 state 不同，後者也必須有適用性依據。bidirectional 的 known value 是 JSON boolean；capture_start／end 是 complete 或 partial；其他 known fact 是非空文字。mode 是 profile 與 manifest 共同使用的明確標籤，不由速率、檔名或副檔名推定。

reset 是否可見放在事件觀測，epoch 的命名及證據放在 facts；知道 epoch 名稱不代表看過 reset。bidirectional 描述該輸入的 capture 證據，不能被當成每個被篩選輸出的雙向覆蓋證明。

Recorded／legacy manifest 的 trace 身分、known facts、field availability 與事件／coverage 聲明必須引用 saved_output、manual_review 或 legacy 類型，且其 `trace_sha256` 與 manifest 相同；文件本身不能滿足此條件。API supported／unsupported 可以引用對應 source 的 applicable、sections_reviewed 正文，或同 trace 觀測。Metadata-only／not_applicable 的文件不能支援 API 聲明；未被用作依據的來源可保持 metadata-only，不因此阻擋其他有觀測來源的資料。

Synthetic fixture 可引用 synthetic evidence，但不能把 origin 改成 recorded 後沿用。這些檢查確認來源角色與宣告身分一致，不會讀 evidence 內容來認證實際真值；合適的來源種類及相同 hash 也不是獨立 qualification。

## 2. 欄位能力與事件觀測分開

| 能力軸 | 可用值 | 意義 |
| --- | --- | --- |
| `api_support` | supported／unsupported／unknown | API 是否支援這個欄位 |
| `applicability` | applicable／not_applicable／unknown | 當前協定／mode／level 是否適用 |
| `availability` | available／unavailable／unknown／not_applicable | 這份輸出實際是否能取得 |

available 必須同時 supported 與 applicable。unsupported 不等於 not_applicable；已支援且適用也可能 unavailable。unknown 不會變成 unsupported。not_applicable 必須在 applicability 與 availability 一致表示。

| 事件 state | count 與要求 |
| --- | --- |
| observed | count > 0；可來自 partial capture，不能因全域 coverage 未知抹掉正向觀測；不能同時宣告 selection excluded |
| not_observed_in_coverage | count = 0，且 selection=included、retention=retained、extraction=complete、filters 已知、有效 inclusive index 起訖已知 |
| unknown | count=null，或有依據的實際輸出 count=0；後者仍不能宣稱事件不存在 |
| not_applicable | count=null、coverage 三軸均 not_applicable、range=null；保留不適用原因的 refs |

`coverage.selection` 記錄 included／excluded／unknown／not_applicable；retention 記錄 retained／dropped／unknown／not_applicable；extraction 記錄 complete／partial／unknown／not_applicable。它們描述輸出選取、保留與抽取完成度，與 trace 的 capture 起訖分開。完整 bounded window 內可證明未觀測到事件，即使整份 capture 是 partial；它不能證明 window 外未發生事件。

USB bad-CRC 預設未輸出與 `SendTransfer(completed=1)` 預設來自 LC-04 p168／170；本輪只把這種差異納入資料語意，不執行 probe，也不反推舊 run 確實漏了哪些包。

## 3. Trace eligibility matrix

矩陣包含 profiles 與 traces。每列嵌入一份 manifest，保留 trace ID、SHA、協定／模式、雙向與 capture 起訖／epoch、已知事件及特殊情境；沒有重新複製 raw trace。每個 profile 都有 slice ID、工程師問題、預期觀測、適用 protocol、精確 mode 清單與至少一個明確 requirement。

每個 profile 自動要求 trace identity、相符 protocol 及已知且相符的 mode。其他 requirement 可檢查：

- fact：`expected=known` 或精確文字／boolean，例如雙向為 true、capture_end 為 complete、epoch 已知。
- field：指定欄位 available；unsupported、unavailable、unknown、not_applicable 的原因分開保留。
- event：指定事件 observed 或 not_observed_in_coverage。
- coverage：指定事件在宣告 index window 內具有完整 coverage。

Requirement 的輸出是 met、missing、unknown 或 not_applicable，附原因與 evidence refs。Matrix status 是 input readiness 摘要：

| Status | 固定計算方式 |
| --- | --- |
| eligible | 所有 requirement（含身分／protocol／mode）都 met |
| partial | 至少一項 met，但仍有未滿足／未知／不適用條件 |
| missing | 沒有任何 met，且至少一項明確不符或不適用 |
| unknown | 沒有任何 met，也沒有明確不符，條件全未知 |

SHA 已知、mode 未知通常是 partial；只知道身分仍不能執行需要特定 mode 的規則。不能只看摘要，逐項原因才顯示缺的是輸入、能力或認知。Matrix validator 重新計算每個 profile 的全部結果，拒絕手改 eligible、漏列 profile 或將 qualification 改成 PASS。

所有 row 的 `qualification` 固定 `NOT_EVALUATED`。這一版驗證**宣告資料的結構及內部一致性**，不能鑑定 evidence 內容真實性、profile 是否足以代表完整規範或 capture 是否真的完整；來源真實性與 profile 的人工審核是未來 U01／P01 的前提。Synthetic fixture 即使 eligible，也只證明契約／計算，不代表某一實際 trace 已資格化。

## 4. 舊資料相容性

本版只辨識兩個明確指定的 legacy 格式；不把任意 JSON 或未知新版本當成舊版接受：

| Legacy 格式 | 已存在的查核入口 | 讀取的身分 |
| --- | --- | --- |
| `pcie.triage-input/v1` | [既有 sample](../samples/pcie/triage-input-hang-p4a.json) | `/trace/sha256` 為分析 trace；有 `/trace/provenance/original_sha256` 才另列原始 trace |
| `usb.demo-source-integrity`（unversioned） | 本機 `c4-demo-regression-20260911/source-integrity.json`；fixture 使用相同形狀的合成資料 | source pass／fail、working_copy pass／fail 的 before／after SHA 各自保留；pass／fail 是歷史角色標籤 |

`legacy_view` 回傳 `s01.legacy-view/v1`，保留 decoded `original` 全部內容及輸入 bytes 的 artifact SHA-256；trace 身分各附原始 JSON pointer。沒有 raw trace 讀取或 hash 重驗，固定 `identity_verification=saved_json_only`、`raw_trace_access=not_checked`、`coverage=unknown`、`qualification=NOT_EVALUATED`。不填 mode、epoch、filter 等推測資料，不將相容性檢視寫回舊檔。

這是相容性／來源檢視，不重新執行 legacy 的全部 validator，也不重驗原 PASS。原資料有互相矛盾的歷史聲明時仍原樣保留，不替它背書。原始 bytes 不變、decoded original 深度相等，與 artifact／analysis trace／original trace 的 hash 分離由測試及本輪保存 JSON 的讀取驗證確認。

W1–W5 的固定 key path-table、USB 大型 timeline 等其他格式沒有加入自動轉換。不能往 W1 `extensions/details` 填新 verdict，也不能把 W1 observation 改寫為 compliance PASS／FAIL。後續整合前先核對相依檔案的 commit／checkout；本輪未跨 checkout 搬動任何實作或 untracked 成果。

## 5. 本地驗收證據與未解限制

本輪結果保存於 [S01 evidence](../artifacts/evidence/s01-offline-contract-20261013/verification.json)，包含測試結果、兩個真實 legacy JSON 的 before／after hash、來源／分析 trace 身分分層、既有檔案保留，以及兩個 checkout 的版本。完整測試輸出同目錄 `tests.txt`。

本地結果：**42 項測試通過**，包含 8 份 manifest × 8 個 profile 的 **64 組手寫 readiness 預期**；另有 profile／expected 表及 2 份 legacy fixture，合計 12 份 JSON。測試涵蓋完整、缺 mode／epoch、partial capture、unknown filter、不適用欄位、矛盾能力、來源角色／錯 trace、隱藏 verdict、legacy 保留與 CLI 拒絕路徑。2 份實際保存 JSON 的相容性檢查只讀取該 JSON，不讀 raw trace。229 個本輪範圍外既有檔案 hash 保持不變，delivery checkout 維持乾淨。

測試依據限本次審查接受的 S01 metadata 不變量、明列的 vendor selection 說明及現有 legacy 格式；它們不是 PCIe／USB wire protocol PASS／FAIL fixtures。未完成的工作仍是實際 coverage probe、欄位／原生 grouping qualification、規格全文與產品政策判定。沒有符合條件的真實 trace 時，即使所有離線測試通過，也不宣稱任何後續 slice 已資格化。

驗收後停在本地 checkpoint。沒有 commit／push／merge，也沒有批准或啟動 U01／P01。
