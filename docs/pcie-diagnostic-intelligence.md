# PCIe 診斷規則盤點與第一個回饋案例

下一個 PCIe 診斷切片以工程師能否從報告找到值得追查的封包為驗收目標。第一案處理 Non-Flit 的 ACK、NAK 和重送。離線程式只執行已審核的規則。AI 協助查找可用規格、分析回饋、提出候選檢查與測試，結果交由工程師審核。

## D1 現有能力

盤點基準為遠端 `main` 的 `e75e88a` 與桌面分支 `codex/pcie-config-ur` 的 `5bea784`。治理分支 `a5c0942` 只包含治理更新。 [main](https://github.com/Gavin0099/lecroy-vse-toolkit/tree/e75e88ad767ba5b2974da437e1d0731021eac131) · [桌面分支基準](https://github.com/Gavin0099/lecroy-vse-toolkit/tree/5bea7848d168a4068ae4df2854b660c056a20fcb)

| 領域 | 現有能力 | 診斷缺口 |
| --- | --- | --- |
| MUX、雙向 L0、速率與寬度 | B1d 套用指定的產品情境與雙向觀察。可評估具明確期待的寬度，速率只在相符樣本範圍內成立。 | 完整 LTSSM 合法性、速率收斂門檻與 Equalization 尚未驗證。 [B1d](pcie-b1d-rule-contract.md) |
| Config Request 與 Completion | B2b 在既有證據範圍內核對 Requester、Tag、對向、Completer 及回覆形狀。UR、CA、CRS 可作狀態證據。 | 完整 Split 配對、Completion Timeout、列舉完成與狀態對產品的影響待補。 [B2b](pcie-b2b-config-contract.md) |
| Register 與跨裝置隔離 | B2a–B2g 保留讀回、寫入意圖與已指定的裝置切換區段。 | 實際生效狀態、ASPM 政策及跨產品套用缺適用條件。 [統一時間線](pcie-unified-timeline.md) |
| NAK、CRC、Recovery | B1e 保存 NAK 明細、CRC 旗標和 Recovery 紀錄。缺 CRC 旗標時維持 UNKNOWN。 | ACK／NAK 序號狀態、Retry Buffer／Replay 和錯誤觸發原因尚未重建。 [B1e](pcie-b1e-findings-contract.md) |
| Flow Control 與錯誤關聯 | 桌面分支可保留部分 DLLP、Link、LTSSM 及電氣閒置事件的觀察。 | 完整 credit 帳本、AER 關聯與 Physical／Data Link 因果仍待驗證。 [VSE phase scan](https://github.com/Gavin0099/lecroy-vse-toolkit/blob/5bea7848d168a4068ae4df2854b660c056a20fcb/scripts/pcie/vopt-phase-scan.pevs) |
| 端到端回饋與報告 | 正式線有來源綁定的離線觀察報告。桌面分支的 `REPLAY-01` 提供人工核對指引。 | 還沒有工程師回饋輸入、候選規則審核到離線執行的路徑。 [報告](pcie-observation-report.md) · [REPLAY-01](https://github.com/Gavin0099/lecroy-vse-toolkit/blob/5bea7848d168a4068ae4df2854b660c056a20fcb/knowledge/pcie/cards/dllp_replay.json) |

桌面線的交易匯出已讀取 TLP 的 `in.PSN`，phase scan 也能讀取 `in.AckNak_SeqNum`。兩份輸出各自有 packet locator，phase scan 每類 ACK、NAK、PM、FC 或其他 DLLP 最多保留 16 筆明細。另外，既有 phase summary 的觀察區段和 channel 只能指向擷取中的位置，尚未證明雙向屬於同一實體 Link 或 Data Link 序號狀態持續。這些欄位可用於設計擷取驗證，現有輸出仍不足以重建任意視窗的未確認序列。 [交易匯出](https://github.com/Gavin0099/lecroy-vse-toolkit/blob/5bea7848d168a4068ae4df2854b660c056a20fcb/scripts/pcie/vopt-transactions.pevs) · [Phase parser](https://github.com/Gavin0099/lecroy-vse-toolkit/blob/5bea7848d168a4068ae4df2854b660c056a20fcb/tools/pcie_phase_evidence.py) · [Stage summary](https://github.com/Gavin0099/lecroy-vse-toolkit/blob/5bea7848d168a4068ae4df2854b660c056a20fcb/tools/pcie_stage_summary.py)

## 工程師回饋案例 3362

| 欄位 | 紀錄 |
| --- | --- |
| 類型 | 工具漏掉值得追查的封包關係 |
| 來源 | 使用者提供的 PETracer 截圖與轉述的工程師觀察，收錄於 2026-11-26 |
| 截圖 SHA-256 | `aafd992b387f3849ef7d4f90edbd8b4240c8db5dbba7cc40e79538781dd85f68` |
| 觀察 | `683771` 為 `R← CplD 3362`，`683772` 為 `R→ ACK 3362`。`683775` 標記 Link Down，其後有兩筆 UpdateFC。`683778` 為 `R→ NAK 3362`，距 Link Down 38.892 µs。`683779` 為 EIEOS，距 NAK 96 ns。 |
| 工程師想解的問題 | Link Down 前後的 Data Link 狀態是否延續，以及當時有沒有尚未確認或重送的 TLP |
| 證據限制 | Packet Number 為截圖顯示索引。來源 trace、顯示副本與其 namespace 尚無驗證綁定。截圖中的 CRC 欄位是顯示值，驗證結果、擷取缺口、實體 Link 對向配對與重送均未知。 |

即使 ACK 與 NAK 的欄位數字相同，若仍在同一個 Data Link 序列且確認界線未前進，`3362` 仍是最後一筆依序收妥的序號。下一個待核對的序號為 `3363`。本案應先在 `683775` 核對 Link Down 前後的狀態，再於 `683778` 核對 NAK 的 CRC、對向和 TLP 重送證據。相同序號可以作為定位線索，規格違反與根因均待確認。

## 候選規則 PCIE-DLL-001

**狀態**　候選，供工程師審核。適用於已確認為 Non-Flit 的單一實體 Link，依 TLP 傳送方向與同一段 Data Link 序號狀態維護 12-bit 序號。規格查閱位置為 PCIe Base Specification Rev. 5.0 v1.0 §3.6.2.1、§3.6.2.2、Figure 3-18 和 §3.6.3.1。上線前須由有權查閱規格的審核者確認適用版本、勘誤與判定前提。 [PCI-SIG 規格入口](https://pcisig.com/PCIExpress/Specs/Base/_5.0_1.0) · [PCI-SIG Link Layer 測試參考](https://pcisig.com/sites/default/files/files/PCI-SIG%20PCIe%205.0%20Compliance%20Webinar_1.25.23_FINAL.pdf)

1. 將有效 ACK／NAK 配到同一實體 Link 上、反向傳送的 TLP。以累積確認界線、實際送出的 TLP 順序與觀測區間維護未確認集合。CRC 驗證失敗的 DLLP 保留原記錄，確認界線保持原值。CRC 未知時保留不確定性。
2. 以 NAK 指示的確認界線找已觀察到的未確認 TLP。`(N + 1) mod 4096` 是第一個要查的序號。若區間內有後續 ACK、尚未確認視窗起始狀態或更早的重送已開始，先重建該時點的確認狀態。
3. 以先前送出和後續再次送出的同一 TLP 為重送候選。至少核對方向、同一序號狀態、PSN、可取得的 TLP 身分及傳輸順序。Link Down 或 Recovery 只有觀察紀錄時暫停承接；有可驗證的狀態延續才延續，確認進入 `DL_Inactive` 時重建序號狀態。
4. 優先輸出可回到 analyzer 的封包、觀察內容、建議核對順序及缺少欄位。第一版結果限於 `OBSERVED`、`CHECK_RECOMMENDED` 與 `INCONCLUSIVE`。缺少可審核的規格與完整證據時，規格違反維持未確認。

### 規格來源及可用於審核的邊界

| 要核對的行為 | 查閱位置 | 候選規則的證據要求 |
| --- | --- | --- |
| 累積確認、12-bit 序號與 Retry Buffer | Base 5.0 v1.0 §3.6.2.1、§3.6.2.2、Figure 3-18 | 反向且 CRC 有效的 DLLP，原送出記錄與當時仍待確認的 TLP。分開看後續 ACK 前進、正在 replay 與 timer 驅動的重送。 |
| Receiver 的序號與 LCRC | §3.6.3.1 | 以同一實體 Link 的同一序列、有效 TLP 與錯誤旗標核對。缺起點或中間封包時保留未知。 |
| 序號狀態的延續與重新初始化 | Chapter 3 Data Link 狀態與 §3.6.2.1、§3.6.3.1 | Recovery 和 analyzer 的 Link Down 是定位錨點。需另外核對 `DL_Inactive` 或狀態延續證據、模式和同一實體 Link。 |

PCI-SIG 公開測試資料提供獨立的反例來源。優先核對 52-10 的 NAK 重送、52-100 的重送順序、52-150 的壞 DLLP CRC、52-170 的錯誤確認序號、53-20 的 Bad LCRC 和 53-31 的重複 TLP。這些是合規測試定位，`PCIE-DLL-001` 目前只可引用為診斷設計的依據。規格入口的全文下載需會員權限。待具授權的工程審核者確認適用版本、ECN 和例外後，再紀錄審核結果與對應測試。 [PCI-SIG 5.0 合規測試](https://pcisig.com/sites/default/files/files/PCI-SIG%20PCIe%205.0%20Compliance%20Webinar_1.25.23_FINAL.pdf) · [PCI-SIG Base 5.0](https://pcisig.com/PCIExpress/Specs/Base/_5.0_1.0)

### 擷取驗收

先驗證一個已授權的 Non-Flit 視窗。沿用現有 VSE 欄位與來源綁定方式，在獨立工作副本上核對來源和顯示副本的 SHA-256、封包 namespace、兩方向的實體 Link 對應、視窗起點狀態與尾端。對照 analyzer 的 packet locator、TLP PSN、DLLP 類型與序號、TLP／DLLP 的 CRC 驗證、Link／LTSSM 和可用的 InitFC 訊號。把 callback 數、輸出數、保留上限、已知 filter 或 decode gap 分開紀錄。兩次擷取的證據對齊且來源保持完整，才可使用該視窗驗證規則。缺視窗起點時能呈現觀察，未確認集合維持未知。

### 回歸案例與預期

| 案例 | 預期 |
| --- | --- |
| ACK 3362，隨後 NAK 3362，同一序號狀態 | 顯示相同累積確認界線與下一個待查序號；規格違反未確認。 |
| 先送過 3363，有效 NAK 3362 後再觀察到相符的 3363 | 顯示重送候選，引用前後 TLP 與 NAK。 |
| NAK 時經完整證據確認沒有未確認 TLP，或其後 ACK 已確認原待送項 | 原先的重送候選更新，缺少重送本身無須提示異常。 |
| 有效 NAK 後重送與已知的未確認集合不符 | 在兩方向覆蓋完整且排除後續 ACK、既有重送與狀態切換時，顯示待核對的差異。 |
| 4095 確認後，下一筆序號為 0 | 算出正確序號與順序。 |
| Recovery 後原序號狀態持續，與確認進入 DL_Inactive 後重建 | 前者有證據才延續；後者清除舊的未確認集合。 |
| 起始狀態不明、裁切、漏封包、未知 CRC 或 epoch 未知 | 保留觀察，判定 `INCONCLUSIVE`。 |
| 兩方向或兩個實體 Link 出現同一 PSN | 證據各自歸於原序列。 |
| ACK 或 NAK 的 DLLP CRC 驗證失敗 | 保留錯誤觀察，序號狀態維持原值。 |

## 回饋到規則

桌面入口先讓工程師選 Packet、選「漏報／誤判／提示無用／補充經驗」，再用一句話描述觀察及想追的問題。可用時自動保存來源與顯示副本的身分、封包 namespace、事件與報告定位。原始回饋與後續查證各自保留，避免 AI 推論覆蓋工程師的原話。

規則資料保留 feedback ID、來源與 locator、適用版本、判定條件、測試結果和審核決定。AI 可依章節索引盤點缺口，將每項標成已可重建、只有觀察、欄位不足或待規格確認。經規格核對、反例測試與獨立審核的版本才進離線執行。公開 repo 保存規格定位、可使用的文字摘要與合成 fixtures，受限規格與客戶原始 capture 留在授權的來源。

| 切片 | 驗收交付 |
| --- | --- |
| D1 規則盤點 | 本頁逐項核對正式線與桌面分支，列出第一個擷取缺口。已完成。 |
| D2 工程師回饋 | 先用 3362 紀錄確認最少欄位與匯出格式，接著驗證工程師能從既有 packet locator 送出並重開同筆回饋。桌面入口待做。 |
| D3 規格知識 | 確認適用規格與欄位，保存候選卡、證據上限和待審核缺口。首卡已擬定，規格審核待做。 |
| D4 Data Link 診斷 | 先通過上述雙向擷取驗收，再用 fixture 驗證 ACK／NAK／Replay 狀態重建。 |
| D5 回饋處理 | 驗證既有 PCIe 分析 skill 能產出可審查的規則、反例與重播紀錄。 |
| D6 報告整合 | 在原本最常用的報告入口顯示找到了什麼、為何值得查及從哪個 Packet 開始。盲測前後都使用同一結果格式。 |

## 如何評估改善

先保留現有報告作基線，開發案例和未參與規則設計的 trace 分開。以同一批盲測 trace 比較兩版，保存每案的有效 finding、誤報、仍漏過的已知問題、工程師是否取得可行下一步，以及從打開報告到定位關鍵封包的時間。分母使用已標註問題數、已審查 findings 或已測案例數，分開記錄。追蹤工程師回饋到核准規則的比例，並每次重跑已修正的回歸案例。單位測試與盲測結果各自保留。

## 已核對的基線

正式 `main` 的 B1d、B1e、B2b、統一時間線及觀察報告現有測試通過 61 項。桌面線的 phase／transaction parser 現有測試通過 15 項。這些結果涵蓋既有輸出和 parser；3362 原始 trace 的新擷取、重送判定及候選規則回歸尚待執行。
