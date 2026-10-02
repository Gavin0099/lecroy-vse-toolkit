# B2g watchlist preparation v2

SOURCE/SCOPE GATE：產品規則待工程師指定，不是 B2g FAILED。以下只解碼 write intent；effective state、expected state 與 policy result 各自保留。

| Packet | Time | Target | Observation | Write intent | ASPM intent | Effective state | Expected state | Policy result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8658 | 8.314 sec | 001:00.0 | L1_ENABLE_WRITE_INTENT | 0x42 | L1 | UNKNOWN | UNKNOWN | NOT_EVALUATED |
| 9915 | 8.314 sec | 001:00.0 | ASPM_DISABLE_WRITE_INTENT | 0x40 | DISABLED | UNKNOWN | UNKNOWN | NOT_EVALUATED |
| 10354 | 8.314 sec | 001:00.0 | L1_ENABLE_WRITE_INTENT | 0x42 | L1 | UNKNOWN | UNKNOWN | NOT_EVALUATED |

CfgWr／Completion acknowledgement 只支持 request 意圖與回覆；不推成 register applied、system ASPM enabled、test condition violation 或 root cause。Read-back 候選 packet 留在 JSON，不自動選擇驗收依據。

需要工程師補的規則：

- Target side and BDF: RC Root Port, EP, or both
- Applicable phase: controller connected, disconnect, SDE reconnect/training, post-L0, or entire testcase
- Per-register side/BDF/phase/register/bits/expected values with definition provenance
- Acceptance basis: write intent sufficient, or read-back / defined equivalent proof required

Layout source: [https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h)

B1d 維持 COMPLETE，既有接通／L0 結果不重開；四項 validation debt 不阻擋 B1d。
