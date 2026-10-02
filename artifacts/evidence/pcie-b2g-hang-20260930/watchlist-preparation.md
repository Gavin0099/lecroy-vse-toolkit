# B2g watchlist preparation

產品 watchlist 的 BDF／階段適用範圍尚未指定，評估 NOT_EVALUATED。以下只解碼 EP write intent，不判定系統 ASPM 已啟用或 hang 根因。

| Packet | Time | Target | Offset | Write intent | ASPM bits | Completion |
| --- | --- | --- | --- | --- | --- | --- |
| 8658 | 8.314 sec | 001:00.0 | 0x90 | 0x42 | 2 | [8660] |
| 9915 | 8.314 sec | 001:00.0 | 0x90 | 0x40 | 0 | [9918] |
| 10354 | 8.314 sec | 001:00.0 | 0x90 | 0x42 | 2 | [10358] |

需要工程師補的規則：

- ASPM requirement target BDF/side and connection stage
- RC control-order register/bit expectations with usable definitions and provenance

Layout source: [https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h)

B1d 維持 COMPLETE，既有接通／L0 結果不重開；四項 validation debt 不阻擋 B1d。
