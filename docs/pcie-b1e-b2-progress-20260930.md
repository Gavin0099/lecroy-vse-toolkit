# PCIe-B1e／B2 進度與停止點

## 結果

2026-09-30 依使用者指示逐段驗證並往下做。B1e、B2a–B2f 在各自已驗證範圍內本地 COMPLETE，
B2g 已整理可重播 decode 證據，產品 watchlist 尚缺工程師的 BDF／階段／期待，
停在此來源關卡。B3 尚未開始。沒有 commit／push／PR／merge。

| Slice | 完成內容 | 驗證 |
| --- | --- | --- |
| B1e | 保留 12 項 B1d 狀態與來源的 link findings，焦點 L0 後 | 7 tests；真實兩次重播一致 |
| B2a | 實際 COM register/data/BE/payload probe | 7 tests；704 TLP／333 rows；兩次 DONE 且原始輸出一致 |
| B2b | 61 config accesses，30 read returns、29 write intents | 7 tests；config completion 關閉 request；兩次重播一致 |
| B2c | Observed capability chain／register mapping | 5 tests；相對位置／未知鏈節點／cut／epoch；兩次一致 |
| B2d | Last read／write intent bytes 分開 | 4 tests；partial masks、zero／UNKNOWN、Completion 時點、epoch |
| B2e | BDF／packet／offset query 與逐 byte evidence | 4 tests；新裝置未知、不借未來、later-write marker |
| B2f | 同 epoch observed diff／跨 epoch 不比較 | 5 tests；source hash 與 snapshot 內容重驗；兩次一致 |
| B2g preparation | 3 筆 EP LinkControl 意圖解碼；缺產品 watchlist 適用範圍 | 3 tests；兩次 preparation 一致；產品 NOT_EVALUATED |

初版全 PCIe suite **180 tests PASS**。該版記錄與 source/script hash：
`artifacts/evidence/pcie-b2g-hang-20260930/verification.json`、`pcie-tests.log`。
原始 trace、舊副本及轉換副本 hash／size／mtime 不變，分析副本保持 read-only。
B1c training、B1d evaluation／工程師問答原內容未改。

## 工程意義

MUX 有雙向 training、雙向 L0 已觀察到。現有 capture 的重新接通後 config
access 是 0；因尾端太短，後續 Gen3 與初始化仍未知，不宣告不存在或失敗。

切換前 EP LinkControl 的最後 write intent 是 Packet 10354 的 0x42，ASPM bits
為 2（L1 enable）。也有早先 0x40 disable intent。沒有 0x90 read-back；
沒有 RC Root Port LinkControl 的相應 observation。故不能推成「系統 ASPM 開啟」
或「此設定造成 BSOD」。公開 register layout 來源為
[Linux v6.12 pci_regs.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h)，
產品期待仍由工程師提供。

舊裝置 state 不沿用到 SDE。Vendor 0x940h[1] 空間／所屬 device／定義未給，
B2h conditional 不自行猜。完整 extended capability chain 缺 0x200 read return，
只限制該段 coverage，不阻擋已證明的 register mapping。

## 無法自行排除的問題

Q8 說 Disable ASPM，但未指出它要求 RC、EP 或兩側、適用於哪個 connection 階段。
B2g 的 RC control-order register／bit／期待值清單亦未提供。
程式能整理 facts，不能替工程師定義這些產品規則。
具體待補清單及 packet/completion evidence 在 `docs/pcie-b2g-engineer-questions.md`。

B1d 保持 COMPLETE，四項 validation debt 不阻擋其第一版；這個停止點是新增
watchlist 的 source/scope gate。補規則後從 B2g 繼續，不回頭重問 MUX 是否接通。

## Owner review 後的 B2g v2

B2g 明列 SOURCE/SCOPE GATE，不是 FAILED。四組最低答案為側與 BDF、phase、
每個 register／bits／expected／來源、write intent 或 read-back／等效 proof 驗收依據。
Packet 10354 命名 `L1_ENABLE_WRITE_INTENT`；每筆 schema 保留 independent
`observed_write_intent`、`effective_state=UNKNOWN`、`expected_state=UNKNOWN`、
`policy_result=NOT_EVALUATED`。即使有後續 read-back 候選，不自動選擇產品驗收規則。

補強 regression：相同 BDF、offset 與 VID/DID 不能繼承前 epoch 的 read／write
intent／capability map；目前不支持 identity-continuity proof 例外路徑。
最新全 PCIe suite **183 tests PASS**，正式 v2 於
`artifacts/evidence/pcie-b2g-hang-20260930/r1-run1/`，兩次重播一致；
`verification-r1.json`／`r1-pcie-tests.log` 是此版驗證。v1 與原 verification 保留歷史。
B1d 與 B1e/B2a–B2f producer 產物未更改；新 v2 input bindings／舊 observation fields 相同。
