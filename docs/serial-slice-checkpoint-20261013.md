# Serial slice checkpoint — 2026-10-13

## 最新續作：P03、I01、I02、P11、P10

本輪按「實作→驗證→review→下一片」完成五個 bounded checkpoint，沒有逐片重新詢問。

- [P03](p03-field-checkpoint-20261013.md)：124筆 DLLP／TLP raw-field 樣本，兩次一致；18個代表
  packet 另以原生文字匯出對照。完整 mode／capture 資格化仍未知，S01 eligibility 不因此變成 eligible。
- [I01／I02](i01-i02-report-checkpoint-20261013.md)：各自新增具型別的 source block。
  W1–W5 與 C5 原模型、歷史結論及評分保留；來源 pointers 可解析，unknown 不渲染成 PASS。
- P04／P05 仍等規範正文、同 epoch 雙向連續觀測與基準；P06 仍等 P02 grouping 身分。
- [P11／P10](p10-p11-observation-checkpoint-20261013.md)：9個有效 Recovery points，另保留 invalid2；
  LinkControl 在 query10360 的 merged／write-intent 值為 ASPM2、CommonClock1、ClockPM0，讀回仍未知。
- P11 曾因 relative OpenFile path 被拒絕，owned cleanup 和失敗證據保留。child PID9464 最後退出，
  native guard 解除，absolute-path 重試成功。當前沒有 native process blocker；P11 已通過限定 state-point review。

證據見 [verification](../artifacts/evidence/p03-serial-20261013/verification.json)；
native failure／cleanup／source identity 保留於同目錄。其餘14個候選仍逐項檢查前提，
加上 U04／U05／P02、G01／G02 的既有門檻，沒有宣稱全部29片完成。

後續沿用既有續作授權；剩餘 stateful／capability／host-log work 仍需適用輸入與來源，沒有提出新的例行批准需求。

## 前一個 checkpoint（歷史範圍）

使用者已授權「實作／驗證／review，無阻擋則接下一片」，不再逐片詢問。這項授權持續適用；資料／規格／工程師定義的門檻沒有取消，不把合成測試通過或未驗證輸入當成資格化。

| Slice | 本地結果與可採用範圍 | 尚缺證據 |
| --- | --- | --- |
| S01 | 前輪離線 contract PASS、review APPROVE；本輪未改 core/schema/fixtures | 仍不認證來源內容真實性 |
| U01 | 7 modes、2次完整成功 run；selection transport 局部 review通過 | bad-CRC獨立例、incomplete樣本、native effective range／filters／capture範圍 |
| U02 | 128 LINK_CMD rows重跑一致；2個raw packets核對兩組info／CRC5位元 | SS實際樣本、LBAD／LGO等未取樣型別、CRC correctness |
| U03 | 128 LFPS rows重跑一致，全部與既有同trace raw資料相符；vendor名稱保存 | 其他type、pattern end、wake／reset成功及量測準確度 |
| U04 | 已做3個精確index的readonly native export；blocked_field | 可確認的state欄名／API值；不猜in.State |
| U05 | 已證實CSV的TRA／XFER native units與獨立namespace；完整資格化HOLD | explicit child-packet refs、payload/status的適用驗證 |
| P01 | 6 profiles重跑一致；named levels與window對帳review通過 | display-hidden對照、effective range／filters及capture／epoch |
| P02 | LINK/SPLIT callback可用；完整grouping資格化HOLD | packet list／bounds、status／metrics完整且不完整的獨立樣本 |
| G01／G02 | 保留工程師 gate | 完整Who／When／What／Proof、vendor定義及已知例子 |
| 其餘19片 | 保留候選與各自實作／資格化門檻，沒有完成聲明 | 詳見29片roadmap；不能越過上游未驗部分或未取得規範正文 |

進度不是「全部片完成」；四片已取得新的局部實證，兩片做了無猜值的discovery。前置的未驗證部分仍限制後續可用結論，既有工程師問題與29片排序保留。後續有相符證據時依現有授權續作，不重新要求常規執行許可。

工程使用價值已具體化：目前可以從 typed observations 找回 LINK_CMD原始word、LFPS raw值與vendor標籤，並直接看到「只是window未選中」和「沒有已資格化coverage」的差別。這不是root cause或certification結果。

入口：[U01](u01-selection-coverage.md)、[U02/U03及U04/U05缺口](usb-field-probes-20261013.md)、[P01](pcie-selection-checkpoint-20261013.md)。Canonical evidence：[verification](../artifacts/evidence/serial-slices-20261013/verification.json)。

兩個 checkout 保留邊界，W1–W5 frozen；沒有把新 verdict 塞到 opaque extensions，也沒有修改既有 extraction／scoring或歷史evidence。所有實際decoder讀取使用獨立唯讀copies，沒有硬體、contact engineer、commit／push／merge／reset／checkout搬動。
