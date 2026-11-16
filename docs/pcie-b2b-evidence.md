# PCIe-B2b：Config Access Log 驗收

2026-09-30 本地 PASS，正式產物 `artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json`
與 `accesses.md`。沒有 commit／push／PR／merge。

## 結果

61 次 config request：32 reads、29 writes。30 個 read 有單一成功、對向、
目標相符及完整 DWORD 的 CplD，可引用 returned value。
225043、225048 的 0x200 reads 位於斷開期間、key 重用且沒有觀察到 completion；
保留未知，不判定 timeout。重新接通後 config request 為 0，仍限這份短 capture。

3207 → 3209 的 offset 0 returned DWORD 為 `0x976717A0`，是切換前 BDF
`001:00.0` 的原始識別值，不當成重新接上的 SDE identity，也不自行替換工程師
所述的 7494 controller 名稱。Vendor 名稱與數值對應尚未建立。

初版沿用 G2b 的「request 不關閉」候選策略，5 筆已完成 config read 被附加
較晚候選而保持 UNKNOWN。這是舊策略的已列限制，不改寫舊 G2b 結果。
本版於完整 config completion 後關閉 pending key；較晚且無 pending request 的
Completion 保留為 unmatched。MRd 仍參與 key 佔用，不能因過濾掉 memory request
就把 CplD 錯認 config data。Memory split completion 完整性未建立。
`run1`、`r1-run1` 為 superseded 歷史；目前只使用 r2。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2b_config_access.py -v`：7 tests PASS。
- 正／反例：partial write mask 保留、memory key 佔用、late completion
  不接到 closed config、key 重用、錯 target／direction／status、coverage 拒絕。
- 真實輸入兩次 JSON／Markdown 位元組相同；`verification.json` 保留 hash 與摘要。
- B1d evaluation 以原 training 重新核對，config／link window 的 TLP 逐筆一致。
  B1c 原 schema 沒有 trace hash，所以 cross-track binding 明列 basename＋重疊
  packets＋同一 G2a metadata，不聲稱 B1c 原已提供 cryptographic trace binding。

## 限制

Write 是 RC request 意圖，不是 hardware applied state；未知值不補零。
前／斷開中／重新接通後分開，BDF 相同也不代表同一裝置。
下一 gate 是從實際 capability pointer／header 解析可觀察到的 register 位置。
