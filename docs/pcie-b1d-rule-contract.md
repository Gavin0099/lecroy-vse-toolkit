# PCIe-B1d 第一版規則契約

範圍：將使用者轉述的工程師產品知識套用到已驗證的 B1c-r1 training.json。
這是單一已指定 MUX 切換區間的離線評估，不新增 trace extraction。

2026-09-30 使用者確認已有資訊足以開始 B1d。數值門檻不完整不阻擋本版；
缺少判定依據的規則保留為 NOT_EVALUATED，證據不足則為 INCONCLUSIVE。

## 輸入與來源

- B1c-r1 `pcie.b1c-training-timeline/v2`，原始 window export 狀態須為 PASS_WINDOW_EXPORT。
- `pcie.b1d-product-context/v1` 明列操作、interposer 位置、切換前後裝置、
  Link Down／重新接通 Link Up 的 packet、產品預期與各規則的工程師回答題號。
- 工程師問答文件；context 保存該文件及 training.json 的完整 SHA-256。
  CLI 驗證兩者後才輸出，防止把其他 case 的 context 套入資料。
- 回覆來源是使用者轉述，收錄日期 2026-09-30；回答人與實際回答日期未提供。
  Case 故障描述是此來源的資訊，不改写舊 extraction JSON 的 UNKNOWN。

本版 context 的 product expectations 為 SDE Gen3 x1、7494 controller Gen2 x1、
切換約 1.4 sec、新 SDE 應重新初始化。工程師未提供「初始 Gen1 合法」的接受規則；
首次有效 L0 前的 2.5 GT/s 只作觀察證據，本版未重新驗證 PCIe spec。
`0x940h[1]` 只記錄原述，不猜 register 定義或執行 register 存取。

## 狀態意義

| 狀態 | 意義 |
| --- | --- |
| PASS | 在本規則明列的觀察範圍內，有資料支持工程師預期；不提升為整個產品成功 |
| FAIL | 已觀察的數值直接違反明確預期；本版用於 sampled width 非 x1 |
| INCONCLUSIVE | 所需觀察不完整，不能判成功或失敗 |
| NOT_EVALUATED | 沒有判定門檻、完成條件或所需可驗證欄位，本版不執行接受度判定 |

不輸出整體 PASS／FAIL。MUX_SWITCH_COMPLETED 和 DEVICE_INITIALIZATION_COMPLETED
分開列出；前者 PASS 僅指符合工程師的雙向 training 證據規則，不是實測 MUX 電氣狀態。

## 規則與驗證條件

| 規則 | 第一版行為 |
| --- | --- |
| 切換 Link Down | 以 context 指定的 Link Down 為切換起點；此事件符合產品情境 |
| 斷開期間 Recovery／Polling／無事件 | 列出 reconnect anchor 前的紀錄與 invalid-state 標記；這些現象本身不判 FAIL，不驗證完整 LTSSM 合法性 |
| MUX 接通 | Q7 的接通依據為 reconnect 後兩方向明確有效的 Polling／Configuration／Recovery 紀錄；不依賴 L0，不能用 carried state 或僅有 Downstream 紀錄代替 |
| 雙向 L0 | 依兩方向明確有效 L0 紀錄成立的獨立觀察里程碑；Q2 是後續初始化情境，L0 不取代 Q7 的 training criterion。缺任一方向為 INCONCLUSIVE |
| Width | reconnect 後 speed_width 或 GUI sample 的 x1 可 PASS，只限這些樣本；任何已觀察非 x1 為 FAIL，無資料為 INCONCLUSIVE |
| 初始 speed 樣本 | 保留相容欄位 INITIAL_GEN1_SAMPLE，但標 assessment_kind=observation_only、INCONCLUSIVE；記錄首次有效 L0 前的 GUI speed／width，不引入工程師未提供的初始 Gen1 接受規則，engineer_questions 為空 |
| 目標 Gen3 | GUI sample 明確看到 8.0 GT/s 可確認曾到達 target；未看到為 INCONCLUSIVE。本版不將未 probe 的 raw speed code 轉成硬性速度判定，也不判定持續停在 Gen1 |
| MUX 斷開時間 | 列出 Link Down 到 context reconnect Link Up 的 display-time 差與約 1.4 sec 的參考值；容許範圍未定，不判 timeout |
| Training timeout | NOT_EVALUATED，沒有適用 spec／起算條件／上限 |
| TS-error tolerance | 列出各 phase HasErrors、時間與 sample-only subtype；NOT_EVALUATED，不自訂「少量／持續」數值，不把整群 384,993 筆都接受 |
| Hot-plug init activity | 雙向 L0 後有 Downstream config request 才標 HOTPLUG_INIT_OBSERVED；只有觀察到 request，不證明回覆、BAR 設定、enumeration 或 emulation 完成；無資料為 HOTPLUG_INIT_NOT_OBSERVED／INCONCLUSIVE |
| 裝置初始化完成 | NOT_EVALUATED，沒有完成 criteria；與 MUX 接通各自保留狀態 |

所有 packet 證據指向 training.json 的 step、inner record、phase 或 GUI sample。
Invalid LTSSM record 可以展示，不能用來成立 training／L0 PASS。
沒有 config request 只描述當前輸入 window，不推定 capture 外從未初始化。
GUI 速度只代表 sample；Data Rate capability 欄位不當作當前 speed。

## 本版驗證計畫

- 正向 fixture：雙向有效 training、L0、x1；初始 Gen1 僅作觀察，Gen3／初始化仍不確定。
- 語意分離 fixture：雙向有效 training 而沒有 L0 時，MUX_CONNECTIVITY=PASS、
  BIDIRECTIONAL_L0=INCONCLUSIVE；只有 L0 紀錄時不能代替 Q7 的 training 證據。
- Target speed 正／負樣本各自使用相符文字，未觀察到 target 時不寫「曾觀察到」。
- 負向 fixture：只有一側 training 或 L0、invalid LTSSM、非 x1、缺 width／GUI speed。
- 邊界 fixture：切換前的 training 不可滿足接通規則；同一 display time 依 packet order；
  config request 不能證明初始化完成；1.4 sec 不能變 timeout；大量 HasErrors 不自動 FAIL。
- 輸入拒絕：錯誤 schema、未通過 window export、不同 input hash、錯誤 anchors、
  重疊 phase、倒置時間、負數 count、孤立 record，以及已有輸出目錄。
- 真實資料：重播現有 hang B1c-r1，核對 packet 1479760、双向 training／L0、
  x1、384,993 HasErrors 與末尾兩筆 message；重播兩次比較輸出位元組與輸入 hash。
- 跑既有 PCIe suite，保留 B1c 及其歷史 PASS；不開啟 VSE／GUI／原始 .pex。

未完成的數值驗證只列為四項 validation debt：training timeout、TS-error tolerance、
Gen3 convergence endpoint／deadline、hot-plug initialization completion criteria。
它們限制對應判定，不阻擋本版產品規則建立。
