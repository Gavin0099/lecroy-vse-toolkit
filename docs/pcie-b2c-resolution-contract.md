# PCIe-B2c：Capability／register 位置解析契約

採用公開 Linux v6.12 `pci_regs.h` 的標準欄位 layout 參考，來源與數值保留於
`pcie-register-reference.json`。這不驗證完整 PCIe spec，也不增加 B1d 規則。
只查公開通用欄位；未向外送 trace／device／故障資料。

每個 connection epoch／BDF 從成功 config returned bytes 取得 header type、
capability pointer 與鏈上 headers；以相對 offset 找 PCIe LinkControl、PMCSR、L1SS。
只在 Completion packet 已到且值已可觀察時採用，不借未來的 read。
Conventional pointer 與 next 要在 0x40–0xFC 且 DWORD-aligned，extended chain
從標準 0x100 起，next 在 0x100–0xFFC 且 aligned；loop／invalid pointer 保留缺口。
Header／中間 node 未觀察到則停在該 node，不猜其 capability ID 或後續 layout。
不能把「未觀察到」當 capability 不存在，切換後不沿用舊 device 的鏈。

本 gate 的 PASS 指 resolver 正反例及真實來源可重播，不要求 capture 已提供完整鏈。
完整鏈與可解析 register 各有獨立 coverage；unknown nodes 不阻擋已證明的 mapping。
Vendor register 不在本版。驗證包含非固定 offset、鏈中缺口／cycle、Completion
前不能使用值、header type unknown 不猜 BAR、跨 epoch 不沿用。
