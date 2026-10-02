# W2＋W3：統一觀察時間線

這個 capability 以既有來源重播 config／TLP 與 bounded link／DLLP，沒有新 extractor、
產品規則、完整逐筆 DLLP／TS export 或 root-cause inference。

## 定稿 invariants 與驗證

| Invariant | Local adversarial evidence |
| --- | --- |
| Capture／source identity 一致 | Metadata bytes、raw COM receipt/output、probe fields、engineer/training hashes；錯來源拒絕 |
| 舊 config 與新 raw DWORD proof 一致 | Full raw replay；333 rows 除 prefix 長度外逐欄相同，舊 prefix 是新 prefix 前綴 |
| Config／policy 準備資料不被改寫 | B2b／B2g／B1d 重算一致；更改 read value 拒絕 |
| 讀回發生於 Completion | Request 不放 read value；Completion 才放 read-return observation，跨 epoch 留空 |
| Packet 與 observation 分開 | 4 overlap TLP 合併 refs；同 packet 的 LTSSM/link/speed 仍各自留觀察 |
| 未配對／缺 Completion 保持未知 | 44 unmatched candidates；225043 沒 Completion，沒有 timeout／read-state 推論 |
| 時間精度與排序 | 原始 display time、0.001 秒 display quantum；同 8.314 秒用 packet order |
| 不虛構 DLLP／TS events | 33 segment count intervals；只一筆明確 NAK，不推 replay |
| GUI sample 不擴大成 population | 三筆 packet sample 置於區間 details；沒有原始 sample time 就不補 timestamp |
| Invalid LTSSM 不當 valid evidence | 原始 valid=0 保留；B1d 重算後才引用其既有 milestone |
| MUX connectivity 與雙向 L0 獨立 | Q7 valid training 支持 connectivity；雙向有效 L0 是獨立觀察 milestone |
| UNKNOWN 不被升級 | Packet 10354 仍 L1_ENABLE_WRITE_INTENT；effective/expected UNKNOWN，policy NOT_EVALUATED |
| 消費者不盲信新增文字 | `verified_timeline` 重算整個 adapter，timeline facts 被改寫就拒絕；report 使用 typed fields |

W1 的 frozen named-field contract 保持；本次 local review 覆蓋 B1/B2 第一次整合邊界，
不以任意 malformed JSON 枚舉擴張規格。

## 真實 capture 的 coverage

- 704 筆 TLP callback records；61 config requests、30 observed read returns、29 write intents。
- Link window 225041..1484414：43 explicit records，含已存在的 4 TLP；新增 39 observations。
- 最終 743 packet observations、738 個不同 packet anchors；這不是整份 capture 的 packet 總數。
- 33 segment intervals 合計 1,259,373 analyzer events、384,993 HasErrors；interval counts 不能加入逐筆 observation 數。
- 9.600..10.912 sec 的 display gap 為 1.312 sec；只說來源 window 沒觀察到事件，不證明電氣靜默。
- 舊 B1 檔沒有直接 capture hash；GUI 宣告 capture、源檔 lineage 與 4 筆 TLP overlap 提供 corroboration，限制永久保留。

## 重播

```text
python -X utf8 -B scripts/pcie/b3b_unified_timeline.py --manifest artifacts/evidence/pcie-unified-timeline-20261002/inputs.json --source-root . --output-dir <new-directory>
python -X utf8 -B scripts/pcie/b3a_event_contract.py --timeline <new-directory>/timeline.json --source-root .
```

輸出既有目錄會拒絕。兩次真實 offline replay 保存於 evidence 的 run1/run2；
來源 input manifest、source hashes／pointers 與 verification.json 足以重播。
這裡重新驗證的是衍生資料，不會重新打開 .pex 或更動硬體。

## 交付範圍

B1d/B1e 保留已驗證範圍；B2g product evaluation 仍 SOURCE_SCOPE_GATE，B2h conditional。
下一個 capability 是 W4+W5 的 Markdown／離線 HTML observation report。
B3c／整體 B3d 與產品 ASPM evaluator 沒有在此完成。
