# PCIe-B1e：Link findings

L0 建立後，是否完成目標升速與新 SDE 裝置初始化？

目前 capture 尾端不足，沒有判定哪一步造成裝置不可見；不重開已有支持的 MUX 接通。

此報告保留 B1d 各項狀態與限制；EXPECTED_CONTEXT 不作異常，證據不足不改成 FAIL，缺門檻不改成 PASS。

| Finding | 項目 | 類別 | 狀態 | 觀察與解讀 |
| --- | --- | --- | --- | --- |
| B1E-001 | 切換起點 Link Down | EXPECTED_CONTEXT | PASS | 指定切換起點出現 Link Down，符合工程師描述的切換情境。 |
| B1E-002 | 接通前的 link 行為 | EXPECTED_CONTEXT | PASS | 接通前已觀察的 Recovery／Polling／無事件區間，屬產品允許出現的現象。 |
| B1E-003 | MUX 接通證據 | SUPPORTED_MILESTONE | PASS | 接通 anchor 後有雙向有效 training，支持工程師的 MUX 已接通判斷。 |
| B1E-004 | 雙向 L0 觀察里程碑 | SUPPORTED_MILESTONE | PASS | 接通後兩方向均有有效 L0 紀錄。 |
| B1E-005 | 連線 width 樣本 | SUPPORTED_MILESTONE | PASS | 接通後已觀察的 width 樣本符合 x1。 |
| B1E-006 | 首次 L0 前速率樣本 | OBSERVATION_ONLY | INCONCLUSIVE | 首次有效 L0 前的 GUI 樣本觀察到 2.5 GT/s x1；本項只記錄觀察。 |
| B1E-007 | 目標 Gen3 樣本 | EVIDENCE_GAP | INCONCLUSIVE | 目前僅確認未在既有 GUI speed 樣本中觀察到 target 8.0 GT/s；window 缺少後續升速證據，不能判定後續是否完成升速。 |
| B1E-008 | 切換事件時間差 | UNEVALUATED_RULE | NOT_EVALUATED | 切換 Link Down 到 reconnect Link Up 的 display-time 差為 1.400 sec，工程師參考值約 1.4 sec。 |
| B1E-009 | Training 時限 | UNEVALUATED_RULE | NOT_EVALUATED | 適用 spec、training 起算條件及 timeout 上限未提供。 |
| B1E-010 | TS-error 接受度 | UNEVALUATED_RULE | NOT_EVALUATED | 輸入 window 共 384,993 筆 HasErrors，保留各段供檢查；容許門檻未定。 |
| B1E-011 | L0 後初始化活動 | EVIDENCE_GAP | INCONCLUSIVE | 雙向 L0 後在輸入 window 未觀察到 config request，後續初始化仍不確定。 |
| B1E-012 | 裝置初始化完成條件 | UNEVALUATED_RULE | NOT_EVALUATED | 初始化／enumeration 完成事件、register 清單與時限未提供。 |

## 後續需要的證據

- speed change / Gen3 convergence
- CfgRd/CfgWr and completions
- VID/DID, BAR and Command state
- device enable / driver-emulation interaction

## B1E-001：切換起點 Link Down

指定切換起點出現 Link Down，符合工程師描述的切換情境。

限制：此事件本身不證明後續接通或初始化成功。

B1d evaluation.json：`/evaluations/0`；rule `SWITCH_LINK_DOWN`。

- Packet 225041：training.json `/phases/0/steps/0`。

## B1E-002：接通前的 link 行為

接通前已觀察的 Recovery／Polling／無事件區間，屬產品允許出現的現象。

限制：不驗證整段 LTSSM 的規範合法性或時間；invalid-state 標記原樣保留。

B1d evaluation.json：`/evaluations/1`；rule `DISCONNECT_ACTIVITY`。

- Packet 225051：training.json `/phases/1/steps/0`。
- Packet 990789：training.json `/phases/1/steps/2`。
- Packet 990799：training.json `/phases/3/steps/0`。
- Packet 1096915：training.json `/phases/3/steps/2`。
- Packet 1096917：training.json `/phases/5/steps/0`。
- Packet 1096918：training.json `/phases/6/steps/0`。
- Packet 1479759-1479760 之間沒有觀察到事件，1.312 sec；`/phases/7`。

## B1E-003：MUX 接通證據

接通 anchor 後有雙向有效 training，支持工程師的 MUX 已接通判斷。

限制：Q7 的依據是雙向有效 training，不要求雙向 L0；未直接量測 MUX 電氣狀態，未證明裝置初始化。

B1d evaluation.json：`/evaluations/2`；rule `MUX_CONNECTIVITY`。

- Packet 1479845：training.json `/phases/9/steps/0`。
- Packet 1484025：training.json `/phases/10/steps/0`。
- Packet 1484046：training.json `/phases/10/steps/1`。
- Packet 1484050：training.json `/phases/10/steps/2`。
- Packet 1484053：training.json `/phases/10/steps/3`。
- Packet 1484072：training.json `/phases/10/steps/4`。
- Packet 1484097：training.json `/phases/10/steps/5`。
- Packet 1484118：training.json `/phases/10/steps/6`。
- Packet 1484147：training.json `/phases/10/steps/7`。
- Packet 1484186：training.json `/phases/11/steps/0`。
- Packet 1484200：training.json `/phases/11/steps/1`。
- Packet 1484216：training.json `/phases/11/steps/2`。
- Packet 1484229：training.json `/phases/11/steps/3`。

## B1E-004：雙向 L0 觀察里程碑

接通後兩方向均有有效 L0 紀錄。

限制：本項是兩方向明確有效 L0 的觀察里程碑；Q2 提供後續初始化情境，不取代 Q7 的 training 接通依據。缺少 L0 不自動判 FAIL，沒有 timeout 上限。

B1d evaluation.json：`/evaluations/3`；rule `BIDIRECTIONAL_L0`。

- Packet 1484273：training.json `/phases/12/steps/0`。
- Packet 1484298：training.json `/phases/12/steps/1`。

## B1E-005：連線 width 樣本

接通後已觀察的 width 樣本符合 x1。

限制：僅限已記錄的 speed_width／GUI 樣本，未確認完整後續連線。

B1d evaluation.json：`/evaluations/4`；rule `LINK_WIDTH_SAMPLES`。

- Packet 1479845：training.json `/phases/9/inner_records/0`。
- Packet 1479761：training.json `/phases/8/gui_samples/0`。

## B1E-006：首次 L0 前速率樣本

首次有效 L0 前的 GUI 樣本觀察到 2.5 GT/s x1；本項只記錄觀察。

限制：工程師只定義 target Gen3 x1 與持續停留 Gen1 不符合預期，未提供初始 Gen1 接受規則；本版未驗證 PCIe spec，不判本項 PASS／FAIL。

B1d evaluation.json：`/evaluations/5`；rule `INITIAL_GEN1_SAMPLE`。

- Packet 1479761：training.json `/phases/8/gui_samples/0`。

## B1E-007：目標 Gen3 樣本

目前僅確認未在既有 GUI speed 樣本中觀察到 target 8.0 GT/s；window 缺少後續升速證據，不能判定後續是否完成升速。

限制：樣本未見 target rate 不等同後續未升速或持續停在 Gen1；升速完成終點／時限未提供，raw speed code 的標示尚未 probe。

B1d evaluation.json：`/evaluations/6`；rule `TARGET_SPEED_OBSERVED`。


## B1E-008：切換事件時間差

切換 Link Down 到 reconnect Link Up 的 display-time 差為 1.400 sec，工程師參考值約 1.4 sec。

限制：這是兩個事件間的時間，非直接量測 MUX dead-time；約 1.4 sec 不作 timeout 或接受門檻。

B1d evaluation.json：`/evaluations/7`；rule `MUX_DISCONNECT_DURATION`。

- Packet 225041：training.json `/phases/0/steps/0`。
- Packet 1479760：training.json `/phases/8/steps/0`。

## B1E-009：Training 時限

適用 spec、training 起算條件及 timeout 上限未提供。

限制：不自訂 Recovery 次數或 training 上限。

B1d evaluation.json：`/evaluations/8`；rule `TRAINING_TIMEOUT`。

- Packet 1484273：training.json `/phases/12/steps/0`。
- Packet 1484298：training.json `/phases/12/steps/1`。

## B1E-010：TS-error 接受度

輸入 window 共 384,993 筆 HasErrors，保留各段供檢查；容許門檻未定。

限制：未自訂 transient／persistent 數值分類；GUI subtype 僅代表已抽樣的紀錄。

B1d evaluation.json：`/evaluations/9`；rule `TS_ERROR_TOLERANCE`。

- Packet 990799-1096915：HasErrors 1，subtype UNKNOWN；`/phases/3`。
- Packet 1096917-1096917：HasErrors 1，subtype UNKNOWN；`/phases/5`。
- Packet 1096918-1479759：HasErrors 382,842，subtype UNKNOWN；`/phases/6`。
- Packet 1479760-1479844：HasErrors 84，subtype UNKNOWN；`/phases/8`。
- Packet 1479845-1484024：HasErrors 2,065，subtype UNKNOWN；`/phases/9`。

## B1E-011：L0 後初始化活動

雙向 L0 後在輸入 window 未觀察到 config request，後續初始化仍不確定。

限制：看到 request 不證明 Completion、BAR 寫入或 enumeration 完成；未看到也不推定 window 外不存在。

B1d evaluation.json：`/evaluations/10`；rule `HOTPLUG_INIT_ACTIVITY`。


## B1E-012：裝置初始化完成條件

初始化／enumeration 完成事件、register 清單與時限未提供。

限制：與 MUX 接通狀態獨立；單一 config request 不構成初始化完成。

B1d evaluation.json：`/evaluations/11`；rule `DEVICE_INITIALIZATION_COMPLETED`。


## 其他原始觀察

NAK 只作 NAK 觀察，不推定 replay；Recovery state 紀錄不當作完整 entry 次數。

- NAK Packet 225042，9.512 sec，seq 1682，Downstream；`/phases/0/inner_records/0`。
- tlp_bad_lcrc：0，僅限 window 內 analyzer flag。
- dllp_bad_crc：0，僅限 window 內 analyzer flag。
- Recovery state 紀錄 9 筆，raw speed/width 紀錄 2 筆；詳細 packet 保留在 JSON，不作規範違反判定。

## Case 來源與未完成驗證

使用者轉述：ASPM disabled; SD7 inserted; device not visible after switching; system hang; BSOD 0x124；不作前段根因推定。

- training_timeout：適用 spec、training 起算條件及 timeout 上限未提供。（不阻擋本版）
- ts_error_tolerance：TS-error 容許筆數、持續時間、起點與適用階段未提供。（不阻擋本版）
- gen3_convergence：Gen3 升速完成的 milestone／觀察時限未提供。（不阻擋本版）
- hotplug_completion：初始化／enumeration 完成事件、register 清單與時限未提供。（不阻擋本版）

## 重播來源

- evaluation_sha256：`22ED4A80E2917FE547693D6BD43AF82CD496C34FFAA5B882DA699622C3EC240A`
- training_sha256：`161FCF9EF28E78D4EAAE7BCB6381A8AEC8A19587FD37964B7B854E8FB366FBD3`
- source_document_sha256：`90CA98E2218E6EBF6D233095392349A5E9EF9396E1A9E239098029B2EAFB04A5`

本版未建立整體產品 PASS/FAIL、電氣量測、規範完整性或 root cause。
