# PCIe LinkControl 原始設定觀測

CATC 合併值、送出的 write intent 與實際 Completion 讀回分開；不能把 enable 視為已進 L1。

RC、device role、這些查詢位置的 LTSSM／PM 訊號、L1SS named fields、CLKREQ# 電氣動作仍未知或未資格化。

## Query packet 3300

# Sidecar register view: P10 LinkControl observed bits - case offset 0x90

Trace SHA-256 C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD; PETracer 13.26.0.43; device 256; epoch before_disconnect; snapshot position packet 3300.
The three value columns are different evidence and are not interchangeable. None of them proves the hardware applied the value.

| Register | Field | CATC merged | Last write intent | Last read-back | CATC native field | Native vs sidecar |
| --- | --- | --- | --- | --- | --- | --- |
| LinkControl 0x90 | ASPM Control[1:0] | UNKNOWN | UNKNOWN @ none | UNKNOWN @ none | Active State PM Control = None | NOT_COMPARABLE_UNKNOWN |
| LinkControl 0x90 | CommonClockConfig[6:6] | UNKNOWN | UNKNOWN @ none | UNKNOWN @ none | Common Clock Configuration = None | NOT_COMPARABLE_UNKNOWN |
| LinkControl 0x90 | EnableClockPowerManagement[8:8] | UNKNOWN | UNKNOWN @ none | UNKNOWN @ none | Enable Clock Power Management = None | NOT_COMPARABLE_UNKNOWN |

Not established:
- catc_merged combines reads and writes (possibly from different times) and is not a hardware readback
- last_write_intent is what was sent, not the applied hardware state
- last_read_back is per byte, latest completion data; it can predate later writes
- scope: one trace, one device, epoch before_disconnect only; other epochs are refused, not inherited
- definition correctness rests on its stated provenance


## Query packet 10360

# Sidecar register view: P10 LinkControl observed bits - case offset 0x90

Trace SHA-256 C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD; PETracer 13.26.0.43; device 256; epoch before_disconnect; snapshot position packet 10360.
The three value columns are different evidence and are not interchangeable. None of them proves the hardware applied the value.

| Register | Field | CATC merged | Last write intent | Last read-back | CATC native field | Native vs sidecar |
| --- | --- | --- | --- | --- | --- | --- |
| LinkControl 0x90 | ASPM Control[1:0] | 2 (L1 Entry Enabled) | 2 (L1 Entry Enabled) @ [10354] | UNKNOWN @ none | Active State PM Control = 2 | MATCH |
| LinkControl 0x90 | CommonClockConfig[6:6] | 1 (Set) | 1 (Set) @ [10354] | UNKNOWN @ none | Common Clock Configuration = 1 | MATCH |
| LinkControl 0x90 | EnableClockPowerManagement[8:8] | 0 (Clear) | 0 (Clear) @ [10354] | UNKNOWN @ none | Enable Clock Power Management = 0 | MATCH |

Not established:
- catc_merged combines reads and writes (possibly from different times) and is not a hardware readback
- last_write_intent is what was sent, not the applied hardware state
- last_read_back is per byte, latest completion data; it can predate later writes
- scope: one trace, one device, epoch before_disconnect only; other epochs are refused, not inherited
- definition correctness rests on its stated provenance

