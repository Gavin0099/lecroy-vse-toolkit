# Observed snapshot：001:00.0 @ Packet 225040

Epoch：before_disconnect。Last read 與 last write intent 分開；不是硬體 snapshot。

| Offset | Width | 名稱 | Last read | Read evidence | Last write intent | Write evidence | Read 後有 write |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0x0 | 4 | VendorDeviceID | 0x976717A0 | [3232] | UNKNOWN | [] | False |
| 0x4 | 2 | Command | 0x406 | [8721] | 0x406 | [8725] | True |
| 0x4 | 4 | raw offset | 0x180406 | [8721] | 0xF9000406 | [8714, 8725] | True |
| 0x8 | 4 | raw offset | 0x8050104 | [3276] | UNKNOWN | [] | False |
| 0xC | 4 | HeaderTypeDWORD | 0x0 | [3288] | UNKNOWN | [8642] | True |
| 0x10 | 4 | BAR0 | UNKNOWN | [] | 0x6C1FF000 | [8599] | False |
| 0x14 | 4 | BAR1 | UNKNOWN | [] | 0x0 | [8604] | False |
| 0x18 | 4 | BAR2 | UNKNOWN | [] | 0x0 | [8609] | False |
| 0x1C | 4 | BAR3 | UNKNOWN | [] | 0x0 | [8614] | False |
| 0x20 | 4 | BAR4 | UNKNOWN | [] | 0x0 | [8620] | False |
| 0x24 | 4 | BAR5 | UNKNOWN | [] | 0x0 | [8625] | False |
| 0x2C | 4 | raw offset | 0x976717A0 | [3304] | UNKNOWN | [] | False |
| 0x30 | 4 | raw offset | UNKNOWN | [] | 0x0 | [8630] | False |
| 0x34 | 4 | CapabilityPointer | 0x80 | [3237] | UNKNOWN | [] | False |
| 0x3C | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [8637] | False |
| 0x80 | 4 | raw offset | 0x2E010 | [3250] | UNKNOWN | [] | False |
| 0x88 | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [8653] | False |
| 0x90 | 2 | LinkControl | UNKNOWN | [] | 0x42 | [10354] | False |
| 0x90 | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [10354] | False |
| 0x92 | 2 | LinkStatus | UNKNOWN | [] | UNKNOWN | [] | False |
| 0xA8 | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [8696] | False |
| 0xB0 | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [8665] | False |
| 0xE0 | 4 | raw offset | 0x80F805 | [8744] | UNKNOWN | [8763] | True |
| 0xE4 | 4 | raw offset | UNKNOWN | [] | 0x6850040 | [8748] | False |
| 0xE8 | 4 | raw offset | UNKNOWN | [] | 0x0 | [8753] | False |
| 0xEC | 4 | raw offset | UNKNOWN | [] | UNKNOWN | [8758] | False |
| 0xF8 | 4 | raw offset | 0xF7C30001 | [3322] | UNKNOWN | [] | False |
| 0xFC | 2 | PMCSR | 0x8 | [8596] | 0x8 | [3330] | False |
| 0xFC | 4 | raw offset | 0x8 | [8596] | UNKNOWN | [3330] | False |
| 0x100 | 4 | raw offset | 0x1081000B | [3260] | UNKNOWN | [] | False |
| 0x108 | 4 | raw offset | 0x11010018 | [3270] | UNKNOWN | [] | False |
| 0x10C | 4 | raw offset | UNKNOWN | [] | 0x0 | [8671] | False |
| 0x110 | 4 | raw offset | 0x1281001E | [3281] | UNKNOWN | [] | False |
| 0x118 | 4 | L1SSControl1 | 0xF | [8678] | 0xF | [8686] | True |
| 0x11C | 4 | L1SSControl2 | 0x28 | [8683] | 0x28 | [8691] | True |
| 0x128 | 4 | raw offset | 0x2001000E | [3293] | UNKNOWN | [] | False |
