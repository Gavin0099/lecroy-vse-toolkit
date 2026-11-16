# PCIe-B2c：Capability／register 解析驗收

2026-09-30 本地 PASS，沒有 commit／push／PR／merge。
正式產物 `artifacts/evidence/pcie-b2c-hang-20260930/run1/capabilities.json`。

## 結果與來源

切換前 `001:00.0` 的 observed conventional chain：0x34 pointer → 0x80 PCIe
→ 0xE0 MSI → 0xF8 PM → 0。因此 LinkControl 在 0x90，PMCSR 在 0xFC。
Observed extended chain：0x100 → 0x108 → 0x110 L1SS → 0x128 → 0x200。
0x200 沒有成功 read return，完整 extended chain 未確立；不能替它命名成 AER。
已觀察到的 L1SS 支持 Control1 0x118、Control2 0x11C。

Layout 參考：[Linux v6.12 pci_regs.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h)。
`reference-check.json` 保留公開 header SHA-256 與逐一相符的 constants；沒有下載
或傳送內部 trace 給外部服務。這是位置／mask 參考，不是 PCIe spec 完整驗證。
切換後 SDE 沒有 config reads，不能沿用舊 device 的 capability map。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2c_capability_resolution.py -v`：5 tests PASS。
- Synthetic PCIe 0x60／PM 0xA0 的相對 offsets、missing node、cycle、invalid pointer、
  duplicate ID、不借未來 completion、不跨 epoch／BDF 沿用都有正反例。
- 真實兩次重播位元組一致，hash 與 gate 收錄於 `verification.json`。

下一 gate 為 B2d last observed state；讀回值與寫入意圖分開，未觀察到不補 0。
