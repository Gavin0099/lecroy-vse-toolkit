# PCIe-B2g：Intent／state／policy 分層契約 v2

本版是產品規則來源準備，不完成產品 policy evaluator。
`pcie.b2g-watchlist-preparation/v2` 的 gate status 為 `SOURCE_SCOPE_GATE`，
與 `policy_result=NOT_EVALUATED` 分開；不是 B2g FAILED。

## 每筆 observation 的三層

| 欄位 | 意義與約束 |
| --- | --- |
| register / bdf / epoch | 標準 register 名稱、目標 BDF、connection epoch；映射有自己的來源 |
| observation_kind | `L1_ENABLE_WRITE_INTENT`、`L0S_ENABLE_WRITE_INTENT` 或 `ASPM_DISABLE_WRITE_INTENT`；只命名 request 意圖 |
| write_value / first_be | 原始 DWORD payload／選中的 byte mask；未選 bytes 不當成寫入 |
| observed_write_intent | LinkControl 16-bit request value；只有兩個 bytes 都被 BE 選中時提供，否則 null |
| aspm_control_requested_bits / aspm_control_intent | Byte 0 已被選中時的 ASPM bits／DISABLED、L0S、L1、L0S_AND_L1 |
| read_back_observed / read_back_evidence_packets | Cut 前後續 read return 候選的存在與 packet；不是 write 已生效的推論 |
| effective_state | 本準備器固定 UNKNOWN；不把 Cpl acknowledgement、read candidate 或 write intent 自動升成生效狀態 |
| expected_state | 工程師尚未提供 scope／phase／register 期待，固定 UNKNOWN；不從 testcase 名稱推導 |
| policy_result | 固定 NOT_EVALUATED；intent 型規則或 state 型規則需工程師選定後，另做來源化 evaluator |

## 最低四組工程師答案

1. 目標側、device／epoch 身分與 BDF：RC Root Port／EP／兩側；同一 BDF 跨 epoch 分列。
2. Phase：controller connected／disconnect／SDE reconnect-training／SDE L0 後／全程。
3. 每項 register／bits 的期待：side、device／epoch、BDF、phase、register、bits、expected、定義來源。
4. 驗收依據：write intent 足夠，或需 read-back／有明確定義的 equivalent proof。

只提供第 1–3 組仍不能替工程師選第 4 組。Test label 與 scope 分開。
未提供規則時，即使某 read candidate 與 write data 相符，也不能評為 policy PASS。
沒有 causal evidence 不命名 root cause。
工程師填入的 device／epoch 是產品規則的適用標籤，不自行成為跨 epoch
identity-continuity proof。此補充只明確化工程師輸入，不改 schema v2 的輸出或驗收結果。

## Epoch invariant

Config read／write-intent state 不跨 device epoch。相同 BDF、offset、數值、
VID/DID 字串或一般 identity hint 不是 explicit identity-continuity proof。
目前沒有 continuity-proof contract／例外路徑，所以一律隔離；未來若支援例外
需獨立的工程師來源、proof schema 與驗證，不因本版文字就自動開放。

## 歷史產物

原 v1／原 verification 保留為歷史。正式 v2 使用
`artifacts/evidence/pcie-b2g-hang-20260930/r1-run1/`，`r1-run2` 為重播證據。
B1d 不改；B1e／B2a–B2f 保持各自已驗證的範圍。
