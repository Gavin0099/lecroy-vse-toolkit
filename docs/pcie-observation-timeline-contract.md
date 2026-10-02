# W1 / B3a：統一觀察時間線 v1

契約版本 `pcie.observation-timeline/v1`；機器可讀欄位表見
`pcie-observation-timeline-contract-v1.json`。stdlib validator 是執行驗收入口。

## 分層

- `events`：具體 packet 上的觀察。多個 layer 在同 packet 可有不同 observation，不能算成多個實體 packet。
- `intervals`：segment counts，沒有個別 packet 或每筆方向。
- `gaps`：來源 window 沒觀察到事件的 display-time 區間；不代表電氣靜默。
- `milestones`：已來源化的 B1d 結果；與 observation 的未知產品期待分開。
- `sources`：byte SHA-256、JSON pointer、capture identity 及 binding 強度。

`CAPTURE_DECLARED` 是來源宣告的 capture hash；`DERIVED_VIA_PROBE` 是經 probe
串接的資料；`CORROBORATED_LEGACY` 是舊 link 資料的交叉核對。
三者不代表同等的直接 capture 雜湊證明。Validator 確認 source bytes 與 pointer；
adapter 必須額外驗證 lineage、重算事實，validator 本身不證明來源真實性。

## 永久邊界

原始 `time_display` 與 `display_quantum_seconds` 同時保留。`8.314 sec` 的
quantum 是 `0.001` 秒，只代表顯示小數位，沒有量測精度或產品 tolerance 的意思。
事件按 packet index 排序；同 packet 用穩定 observation ID 排列，不能建立 layer 先後因果。

`routing_bdf` 只描述路由；`device_identity=UNKNOWN`、continuity proof=null。
依斷開／重接 anchor 計算 epoch。v1 不提供跨 epoch 繼承例外；BDF／VID-DID 相同也不接受。

每筆 observation 的 `state_claims` 固定 effective/expected UNKNOWN、policy NOT_EVALUATED。
讀回值與 write intent 保留在不同 details；不把 Completion 當 applied proof。
B1d 的 MUX connectivity 與雙向 L0 使用獨立 milestone，不能互相替代。

## 驗證

`python -X utf8 -B scripts/pcie/b3a_event_contract.py --timeline artifacts/evidence/pcie-w1-20261002/representative.json --source-root .`

Fixture 來自已交付 B2g v2 的兩筆真實 write intent，源檔以 hash/pointer 綁定。
負面測試涵蓋錯 capture、缺 source、修改 byte、失效 pointer、epoch/identity 推測、
相同時間下倒序、重複 observation、錯 precision、policy 升級與路徑逸出。
此 slice 不產生完整 timeline，也不新增產品或 PCIe spec 規則。

契約欄位集合固定；未宣告欄位拒絕。額外 provenance／coverage 資料使用 `extensions` 或 record `details`，所有深度的 reserved state/policy keys 同樣保持 UNKNOWN／NOT_EVALUATED。

Segment total 必須等於其連續 packet span，類別及 error counts 各自不得超過 total；error flags 可能重疊，不相加當事件總數。Gap 僅對宣告的 source coverage 生效，拒絕同來源的區間內事件；不將其他 source 的 coverage 偷擴張過來。
