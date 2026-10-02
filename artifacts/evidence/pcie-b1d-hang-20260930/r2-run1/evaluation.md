# PCIe-B1d：MUX 切換產品規則評估

本報告逐項比對工程師預期與既有 trace 觀察。PASS 只限各項所列證據，沒有整體產品成功判定。

工程師回答來源：`docs/pcie-b1d-engineer-questions.md`，收錄日期 2026-09-30；由使用者轉述，回答人／實際日期未提供。

故障描述（使用者轉述）：ASPM disabled; SD7 inserted; device not visible after switching; system hang; BSOD 0x124。其他測試的 0xA0 不套用到本 case。

判讀順序是 MUX 接通 → 雙向 L0 → 目標升速 → 新裝置初始化。各階段獨立；雙向 training 支持接通，不能證明後續裝置可見。

| 項目 | 狀態 | 觀察與解讀 | 工程師來源 |
| --- | --- | --- | --- |
| SWITCH_LINK_DOWN | PASS | 指定切換起點出現 Link Down，符合工程師描述的切換情境。 | Q1 |
| DISCONNECT_ACTIVITY | PASS | 接通前已觀察的 Recovery／Polling／無事件區間，屬產品允許出現的現象。 | Q1, Q2, Q3 |
| MUX_CONNECTIVITY | PASS | 接通 anchor 後有雙向有效 training，支持工程師的 MUX 已接通判斷。 | Q7 |
| BIDIRECTIONAL_L0 | PASS | 接通後兩方向均有有效 L0 紀錄。 | trace observation；Q2 提供後續初始化情境 |
| LINK_WIDTH_SAMPLES | PASS | 接通後已觀察的 width 樣本符合 x1。 | Q4 |
| INITIAL_GEN1_SAMPLE | INCONCLUSIVE | 首次有效 L0 前的 GUI 樣本觀察到 2.5 GT/s x1；本項只記錄觀察。 | trace 觀察；無工程師接受規則 |
| TARGET_SPEED_OBSERVED | INCONCLUSIVE | 目前僅確認未在既有 GUI speed 樣本中觀察到 target 8.0 GT/s；window 缺少後續升速證據，不能判定後續是否完成升速。 | Q4 |
| MUX_DISCONNECT_DURATION | NOT_EVALUATED | 切換 Link Down 到 reconnect Link Up 的 display-time 差為 1.400 sec，工程師參考值約 1.4 sec。 | Q1, Q3 |
| TRAINING_TIMEOUT | NOT_EVALUATED | 適用 spec、training 起算條件及 timeout 上限未提供。 | Q2, Q3 |
| TS_ERROR_TOLERANCE | NOT_EVALUATED | 輸入 window 共 384,993 筆 HasErrors，保留各段供檢查；容許門檻未定。 | Q5 |
| HOTPLUG_INIT_ACTIVITY | INCONCLUSIVE | 雙向 L0 後在輸入 window 未觀察到 config request，後續初始化仍不確定。 | Q2, Q6 |
| DEVICE_INITIALIZATION_COMPLETED | NOT_EVALUATED | 初始化／enumeration 完成事件、register 清單與時限未提供。 | Q2, Q6 |

PASS 表示此項觀察符合預期；FAIL 表示已觀察數值違反明確預期；INCONCLUSIVE 表示證據不足；NOT_EVALUATED 表示判定条件未定。

本 window 的最後觀察為 Packet 1484414（10.912 sec）。
雙向 L0 到 window 尾端的 display-time 差為 0.000 sec（None 表示尚無雙向 L0）；顯示時間無差不代表物理時間為零。

## SWITCH_LINK_DOWN：PASS

指定切換起點出現 Link Down，符合工程師描述的切換情境。

限制：此事件本身不證明後續接通或初始化成功。

- Packet 225041：9.512 sec；training.json `/phases/0/steps/0`。

## DISCONNECT_ACTIVITY：PASS

接通前已觀察的 Recovery／Polling／無事件區間，屬產品允許出現的現象。

限制：不驗證整段 LTSSM 的規範合法性或時間；invalid-state 標記原樣保留。

- Packet 225051：9.512 sec Downstream RECOVERY valid=1；training.json `/phases/1/steps/0`。
- Packet 990789：9.538 sec Downstream RECOVERY valid=1；training.json `/phases/1/steps/2`。
- Packet 990799：9.552 sec Downstream RECOVERY valid=1；training.json `/phases/3/steps/0`。
- Packet 1096915：9.563 sec Downstream RECOVERY valid=1；training.json `/phases/3/steps/2`。
- Packet 1096917：9.575 sec Downstream RECOVERY valid=1；training.json `/phases/5/steps/0`。
- Packet 1096918：9.575 sec Downstream POLLING valid=0；training.json `/phases/6/steps/0`。
- 沒有觀察到事件：9.600 sec-10.912 sec（1.312 sec），Packet 1479759 與 1479760 之間；`/phases/7`。

## MUX_CONNECTIVITY：PASS

接通 anchor 後有雙向有效 training，支持工程師的 MUX 已接通判斷。

限制：Q7 的依據是雙向有效 training，不要求雙向 L0；未直接量測 MUX 電氣狀態，未證明裝置初始化。

- Packet 1479845：10.912 sec Upstream POLLING valid=1；training.json `/phases/9/steps/0`。
- Packet 1484025：10.912 sec Downstream CONFIG valid=1；training.json `/phases/10/steps/0`。
- Packet 1484046：10.912 sec Upstream CONFIG valid=1；training.json `/phases/10/steps/1`。
- Packet 1484050：10.912 sec Upstream CONFIG valid=1；training.json `/phases/10/steps/2`。
- Packet 1484053：10.912 sec Downstream CONFIG valid=1；training.json `/phases/10/steps/3`。
- Packet 1484072：10.912 sec Downstream CONFIG valid=1；training.json `/phases/10/steps/4`。
- Packet 1484097：10.912 sec Upstream CONFIG valid=1；training.json `/phases/10/steps/5`。
- Packet 1484118：10.912 sec Downstream CONFIG valid=1；training.json `/phases/10/steps/6`。
- Packet 1484147：10.912 sec Upstream CONFIG valid=1；training.json `/phases/10/steps/7`。
- Packet 1484186：10.912 sec Downstream RECOVERY valid=1；training.json `/phases/11/steps/0`。
- Packet 1484200：10.912 sec Upstream RECOVERY valid=1；training.json `/phases/11/steps/1`。
- Packet 1484216：10.912 sec Upstream RECOVERY valid=1；training.json `/phases/11/steps/2`。
- Packet 1484229：10.912 sec Downstream RECOVERY valid=1；training.json `/phases/11/steps/3`。

## BIDIRECTIONAL_L0：PASS

接通後兩方向均有有效 L0 紀錄。

限制：本項是兩方向明確有效 L0 的觀察里程碑；Q2 提供後續初始化情境，不取代 Q7 的 training 接通依據。缺少 L0 不自動判 FAIL，沒有 timeout 上限。

- Packet 1484273：10.912 sec Downstream L0 valid=1；training.json `/phases/12/steps/0`。
- Packet 1484298：10.912 sec Upstream L0 valid=1；training.json `/phases/12/steps/1`。

## LINK_WIDTH_SAMPLES：PASS

接通後已觀察的 width 樣本符合 x1。

限制：僅限已記錄的 speed_width／GUI 樣本，未確認完整後續連線。

- Packet 1479845：10.912 sec；training.json `/phases/9/inner_records/0`。
- Packet 1479761：GUI sample 2.5 GT/s x1 subtype=TSRsrvErr（僅代表此 sample）；training.json `/phases/8/gui_samples/0`。

## INITIAL_GEN1_SAMPLE：INCONCLUSIVE

首次有效 L0 前的 GUI 樣本觀察到 2.5 GT/s x1；本項只記錄觀察。

限制：工程師只定義 target Gen3 x1 與持續停留 Gen1 不符合預期，未提供初始 Gen1 接受規則；本版未驗證 PCIe spec，不判本項 PASS／FAIL。

- Packet 1479761：GUI sample 2.5 GT/s x1 subtype=TSRsrvErr（僅代表此 sample）；training.json `/phases/8/gui_samples/0`。

## TARGET_SPEED_OBSERVED：INCONCLUSIVE

目前僅確認未在既有 GUI speed 樣本中觀察到 target 8.0 GT/s；window 缺少後續升速證據，不能判定後續是否完成升速。

限制：樣本未見 target rate 不等同後續未升速或持續停在 Gen1；升速完成終點／時限未提供，raw speed code 的標示尚未 probe。


## MUX_DISCONNECT_DURATION：NOT_EVALUATED

切換 Link Down 到 reconnect Link Up 的 display-time 差為 1.400 sec，工程師參考值約 1.4 sec。

限制：這是兩個事件間的時間，非直接量測 MUX dead-time；約 1.4 sec 不作 timeout 或接受門檻。

- Packet 225041：9.512 sec；training.json `/phases/0/steps/0`。
- Packet 1479760：10.912 sec；training.json `/phases/8/steps/0`。

## TRAINING_TIMEOUT：NOT_EVALUATED

適用 spec、training 起算條件及 timeout 上限未提供。

限制：不自訂 Recovery 次數或 training 上限。

- Packet 1484273：10.912 sec Downstream L0 valid=1；training.json `/phases/12/steps/0`。
- Packet 1484298：10.912 sec Upstream L0 valid=1；training.json `/phases/12/steps/1`。

## TS_ERROR_TOLERANCE：NOT_EVALUATED

輸入 window 共 384,993 筆 HasErrors，保留各段供檢查；容許門檻未定。

限制：未自訂 transient／persistent 數值分類；GUI subtype 僅代表已抽樣的紀錄。

- Packet 990799-1096915，9.552 sec-9.563 sec：HasErrors 1，subtype UNKNOWN；`/phases/3`。
  - GUI Packet 990799：TSDataRateErr,TSRsrvErr,TSLaneErr,TSTrainingControlErr（僅代表此 sample）。
- Packet 1096917-1096917，9.575 sec-9.575 sec：HasErrors 1，subtype UNKNOWN；`/phases/5`。
- Packet 1096918-1479759，9.575 sec-9.600 sec：HasErrors 382,842，subtype UNKNOWN；`/phases/6`。
  - GUI Packet 1096918：TSRsrvErr（僅代表此 sample）。
- Packet 1479760-1479844，10.912 sec-10.912 sec：HasErrors 84，subtype UNKNOWN；`/phases/8`。
  - GUI Packet 1479761：TSRsrvErr（僅代表此 sample）。
- Packet 1479845-1484024，10.912 sec-10.912 sec：HasErrors 2,065，subtype UNKNOWN；`/phases/9`。

## HOTPLUG_INIT_ACTIVITY：INCONCLUSIVE

雙向 L0 後在輸入 window 未觀察到 config request，後續初始化仍不確定。

限制：看到 request 不證明 Completion、BAR 寫入或 enumeration 完成；未看到也不推定 window 外不存在。


## DEVICE_INITIALIZATION_COMPLETED：NOT_EVALUATED

初始化／enumeration 完成事件、register 清單與時限未提供。

限制：與 MUX 接通狀態獨立；單一 config request 不構成初始化完成。


## 待補驗證條件

下列項目限制相應規則，沒有阻擋本版建立與重播。

- training_timeout：適用 spec、training 起算條件及 timeout 上限未提供。
- ts_error_tolerance：TS-error 容許筆數、持續時間、起點與適用階段未提供。
- gen3_convergence：Gen3 升速完成的 milestone／觀察時限未提供。
- hotplug_completion：初始化／enumeration 完成事件、register 清單與時限未提供。

## 輸入保留的未知項

- `HasErrors` 在 GUI 抽樣中對應 analyzer 的 Training Sequence Error，但只看了 3 筆；各階段 `HasErrors` 的子類型分布為 `UNKNOWN`。
- 單一階段內的 TS1、TS2、DLLP 等計數沒有按方向拆開；方向拆分只到 B1c-x2 的 R1、R2、R3 範圍層級。
- speed code 的 GT/s 標示來自 VSE 手冊文字，未經 probe 驗證。
- B1c-x2 樣本沒有出現 `_CHANNEL_1` 的名稱，範圍統計以 channel id 列出。

## 重播來源

training.json SHA-256：`161FCF9EF28E78D4EAAE7BCB6381A8AEC8A19587FD37964B7B854E8FB366FBD3`
context SHA-256：`78BDE038BCADEE0C12384F149247C5B22A8BD2FBBACFB0D06AC01CF4B3CBF691`
工程師問答 SHA-256：`90CA98E2218E6EBF6D233095392349A5E9EF9396E1A9E239098029B2EAFB04A5`

未建立 BSOD 根因、初始化完成、持續 Gen1、整體 PASS／FAIL 或跨 case 正確性。
