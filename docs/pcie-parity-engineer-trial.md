# PCIE-05：r6／r7.1 工程師盲測

2026-10-20：依使用者交付審查，**凍結 r7.1，先試用再決定 r8**。
本機封裝驗證已完成；本文件準備好不代表工程師盲測已開始或通過。
目前工程師、合格陌生 trace 與實測結果均待提供。這輪只更新文件，
不修改程式、規則或已交付 ZIP；本文件作為凍結 ZIP 之外的試用補充說明。

## 本輪版本與樣本

| 版本 | 凍結 ZIP | SHA-256 |
|---|---|---|
| A：r6 | `USB-PCIe-Trace-Triage-Stage-20261020-r6.zip` | `884fadf757b53364ae3ddb612297e648f4452de3bf48cde89d35b9513cba0bcd` |
| B：r7.1 | `USB-PCIe-Trace-Triage-Flow-20261020-r7.1.zip` | `a694c0c4e7571a2cd4f61ccba65c0e38cd3bc1b2aed8bf98e6fc8e19e30f8263` |

至少兩位不熟悉測試資料的工程師、四份未參與開發的 trace。由答案保管人
預先查驗樣本資格，記錄 source SHA、取得來源、是否曾調規則、是否只是
既有案例的裁切／轉換／重擷取，以及獨立參考證據。不能直接把開發資料
夾中另一份 trace 視為盲測樣本。無獨立答案者可做探索，正確性填 UNKNOWN。

| 情境（僅答案保管人可見） | 本輪要驗證的判讀 |
|---|---|
| 正常 Hot Plug | 未給情境時保持未知；給定適用的操作情境後，不把預期 Link Down 當故障 |
| Link Training 異常 | 能指向相關 Training 階段，區分已觀察異常與擷取缺口 |
| L0 後初始化未完成 | 區分單方向 L0、裝置身分與初始化證據，不自行宣告成功 |
| 一般 Transaction 問題 | Flow-first 不隱藏有證據的重要 Packet 異常，工程師能進入次要交易核對 |

匿名編號 T1～T4 不固定對應上表順序。不要將情境／答案放進工程師看到的
檔名；需要匿名副本時保持內容及 hash 相同，保留原檔。內嵌註記若洩漏
答案，記錄盲測受限，不能偷偷修改原始 capture。

## 八次交叉操作

先用不在評分集內的練習 trace 熟悉兩版操作。兩位工程師獨立進行，
完成全部指定案例前不互相交流答案。同一工程師每份評分 trace 只看一次。

| 次序 | 工程師 E1 | 工程師 E2 |
|---|---|---|
| 1 | T1／r6 | T4／r7.1 |
| 2 | T2／r7.1 | T3／r6 |
| 3 | T3／r7.1 | T2／r6 |
| 4 | T4／r6 | T1／r7.1 |

每份 trace 各由一位工程師用 r6、一位用 r7.1；版本順序為 ABBA／BAAB。
兩版使用同一台機器或記錄環境差異，固定原生軟體版本、顯示設定、
匯入方式及快取條件。兩版串行執行，不同時搶用原生 session。
這是小樣本探索比較，不足以宣稱通用正確率或統計上的效率提升。

## 每次操作與計時

1. 匯入匿名單檔；不提供失敗時間、Packet、PASS baseline 或答案標記。
   記錄 ZIP、source／display SHA、namespace 與 PETracer 精確版本。
2. 記錄匯入開始 `t0`、第一屏可操作 `t1`、工程師首次提出核對階段 `t2`、
   點原生定位 `t3`、正確原生位置可見 `t4`、工程師完成線索核對 `t5`。
   第一眼辨識為 `t2−t1`；定位為 `t4−t3`；總流程以 `t5−t0` 直接量測。
   不用不同測試的耗時相加推估總時間。若有多次定位，逐次記錄。
3. 在揭露答案前，保存工程師對「已觀察／推論／UNKNOWN」的說明、
   第一個核對階段、前三項建議是否縮小範圍、無關方向及未找到的結果。
   無結果、逾時、放棄與恢復成本均保留，不只計成功操作。
4. 鎖定首次判讀後，才提供預先準備、兩版一致的操作情境資料。
   僅給實際操作與適用範圍，不給答案時間／Packet。再記錄判讀是否改善，
   與額外閱讀／重新分析時間；與無情境首輪分開評分。
   r6 若無對應輸入功能，照實記為由工程師人工使用情境，不模擬功能存在。
5. 核對實際顯示副本、Packet、時間、方向；自動定位與 Ctrl+G fallback
   分開記錄。結束定位後檢查清理和原檔，保存報告與操作日誌。
6. 所有首次判讀鎖定後，答案保管人才揭露參考證據，標記正確、有幫助
   但不足確認、錯誤或無法判定。工程師若無法用語言說明，不能由測試者代答。

### 每次複製一份紀錄

| 欄位 | 實際結果 |
|---|---|
| E1／E2、T1～T4、版本、次序、日期、先前接觸情況 | 待填 |
| ZIP／source／display SHA、namespace、Windows／PETracer、螢幕配置 | 待填 |
| 樣本資格、參考證據保管人、答案是否外洩 | 待填 |
| t0、t1、t2、每次 t3／t4、t5；中斷／逾時／恢復 | 待填 |
| 第一個調查階段及理由、是否與獨立證據相符 | 待填 |
| 前三項有用建議數、讀過的總建議數、重複文案造成的困擾 | 待填 |
| 無關／錯誤方向個數、回頭步驟、重要 Packet 是否被忽略 | 待填 |
| 是否分清觀察／推論／故障、Coverage UNKNOWN、排序與時間精度 | 待填 |
| 無情境首次判讀／補情境後判讀；情境來源、範圍、額外耗時 | 待填 |
| 原生檔案／Packet／時間／方向、自動或 fallback、失敗原因 | 待填 |
| 正常 Hot Plug 誤判／L0 誤認初始化／真正異常被掩蓋 | 待填 |
| 無結果是否合理、尚缺證據、工程師原話與相關來源 | 待填 |
| 結束定位／原檔保全／既有 session 是否受影響 | 待填 |
| 裁定：正確／有幫助但未確認／錯誤／UNKNOWN；證據及裁定人 | 待填 |

5 秒辨識是觀察目標，必須同時找對方向，不能單憑速度判 PASS。
比較每份 trace 的兩版結果並保留工程師差異；不要把八次操作當成八份
獨立 trace。r6 與 r7.1 的比較不等於相對純手動 LeCroy 的省時率；
若要聲稱後者，需另安排未見過且難度可比的手動案例及正確性評分。

## r8 決策依據

| 真人觀察到的主要問題 | 優先考慮的工作 |
|---|---|
| 有證據可用，但前三項無法縮小範圍或重複建議負擔大 | Flow Ranking／Next Action Aggregation |
| 判斷主要被必要證據缺口限制 | 對應缺口的 Split／實體 Link／Coverage |
| 結果有用且正確，但等待佔主要成本 | VSE 擷取效能與原生定位延遲 |

先列實例、頻率、造成的錯誤方向／耗時，再決定切片；目前三者都不是已批准
的 r8 實作。定位錯檔、原檔變動或把正常行為明確誤判為故障，須個別記錄
並重新評估受影響的試用範圍，不能以平均加速抵銷。

使用限制見 [使用說明](usb-pcie-tool-usage.md)；
本機證據見 [r7.1 資格報告](pcie-r71-qualification-20261020.md)。
下面保留較早的試用規劃作歷史參考；本輪版本與分派以上述安排為準。

## 歷史規劃：r6 與 r3 比較文件

Historical trial candidate: **r6**. Follow
[QUAL-01/02 procedure](pcie-r6-qualification-plan-20261020.md) and the
[r6 Delta Qualification](pcie-r6-delta-qualification-20261020.md).
The r3 comparison below is historical, not the latest package selection.
r6 has actual product main-view navigation evidence on PETracer13.26.0.43;
human usefulness, native cancellation, other versions and unseen cases remain pending.

PCIE-05 is not passed by developer tests or screenshots. Use an unfamiliar
capture that did not tune the existing G3 rules. Record the exact package SHA,
PETracer version, source SHA, display SHA and namespace. Keep the original trace
unchanged. Do not supply failure time, PASS/FAIL filename labels or a baseline to
discovery. Engineer annotations are used only after discovery for scoring.

## One trial

### Two-round comparison: workflow baseline vs. UX revision

Keep both packages immutable:

| Arm | Package | SHA-256 |
|---|---|---|
| A: workflow baseline | USB-PCIe-Trace-Triage-20261019.zip | 1f1c467bf0ac011ce8d8f6051e70ecd84163ff4bfac5227ce581bffe97266509 |
| B: issue-first UX, historical | USB-PCIe-Trace-Triage-UX-20261019-r3.zip | Record and verify the delivered r3 ZIP SHA from the release receipt before trial |

The immutable r2 UX package (`5ea006d7c6e8649b1b1a9840b89f700a16ab39395bbb8dd9cd0abdfadfb4e222`)
is retained as historical evidence. A real picker import exposed Unicode IPC
encoding failure under the Traditional Chinese Windows code page. r3 fixes
that shared import path; it does not change the UX rules or protocol analysis.
If arm A cannot import the assigned Unicode path, record the failure and cost;
do not silently rename inputs or count it as a visual-recognition improvement.

Use different unfamiliar traces matched for protocol, capture size, evidence
completeness and task difficulty. Assign cases before timing; record how they
were matched. Counterbalance AB/BA across engineers or matched tasks when
possible. Do not show the known failure time, annotations or PASS/FAIL labels
before discovery. A second pass on an already solved capture is UI practice,
not independent timing evidence. Developer screenshots/replay are not either
human round. Keep correctness and misleading recommendations beside every
timing result; do not report savings from speed alone.

Measure first-target recognition from the fully displayed result screen, and
measure navigation from candidate selection to the engineer seeing the correct
native Packet/Transfer. For PCIe this includes Ctrl+G, file/time/direction
verification and any context switching. Also record total import-to-confirmed-
lead time separately. All human timing/result cells remain Pending.

### Per-round procedure

1. Start the same desktop workspace used for USB. Import/drop one `.pex`.
2. Record loading, extraction and analysis time. Check scope, candidate count
   and the explicit capture-order label before selecting a candidate.
3. Explain the candidate's observation, reason and next check in your own words.
4. Open the owned working copy using the PETracer button. In r6, first verify
   automatic main-view positioning; record Ctrl+G fallback separately if used.
   Verify file, Packet, direction and time. Historical r3 used manual Ctrl+G.
5. Record whether the first three candidates contained a useful lead, how many
   irrelevant leads were inspected, and whether any missing evidence was clear.
6. Export HTML/Markdown, then finish navigation. Confirm the engineer's other
   native work was not changed. If another PETracer session was already open,
   expect restricted-mode refusal; record its practical cost.
7. Compare against the original LeCroy workflow on a separately assigned case
   or counterbalanced order. Do not call repetition on a now-familiar capture a
   fair independent timing comparison.

## Record per case

| Field | Actual observation |
|---|---|
| Engineer / date / package SHA / PETracer version | Pending |
| Arm A or B / order / matched-case rationale / prior exposure | Pending |
| Source/display SHA / namespace / prior familiarity | Pending |
| Original workflow total minutes / correctness | Pending |
| Tool import + analysis seconds | Pending |
| Read candidates + native navigation + verification seconds | Pending |
| Total tool workflow minutes / correctness | Pending |
| Useful lead in first three / irrelevant candidates inspected | Pending |
| Packet/time/direction match / false or misleading interpretation | Pending |
| Missing coverage understood / recovery confusion | Pending |
| Engineer recommendation / specific UI problem | Pending |
| First target identified within 5 seconds / actual seconds | Pending |
| Candidate selection to correct native Packet/Transfer seconds | Pending |
| Coverage / time precision / ordering interpreted correctly | Pending |
| Steps, backtracking and wrong directions before verified lead | Pending |
| Distinguishes observation, candidate and root cause / example | Pending |
| PM or NAK mistaken for failure / subset verification mistaken for whole-trace PASS | Pending |
| Expand evidence / locate selected source / keyboard focus confusion | Pending |

The 5-second target is measured from the first result screen, with no prior
hint about the fault position. Screenshots and developer replay cannot pass
this criterion. The repository's `docs/trace-ux-issue-first-plan-20261019.md`
records the design rationale; packaged `usb-pcie-tool-usage.md` explains usage.

Report a time-saving percentage only when both totals and correctness are
observed. No threshold or completion result is filled with example numbers.

## Separate open qualifications

- New independent PCIe captures, large capture stress and different display filters.
- Other PETracer versions and a clean Windows machine with no developer Python.
- Physical drag/drop by an engineer; scripted IPC and picker checks are separate.
- Native modal/hang behavior on the engineer's machine. Worker timeout tests do
  not establish native cancellation.
- Historical r3 API readback/manual fallback did not establish main-view
  navigation. r6 product navigation is locally verified on13.26.0.43; other
  versions and engineer operation remain separate pending qualifications.
