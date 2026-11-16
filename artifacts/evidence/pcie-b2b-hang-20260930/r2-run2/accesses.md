# PCIe-B2b：Config access log

此表列出 RC request 與 trace 中的回覆；寫入意圖不等同硬體生效。切換前 state 不沿用到新裝置。

| Packet | 時間 | Epoch | Type | Target | Offset (bytes) | BE | Write | Read return | Completion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3148 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xF8 | 0xF/0x0 | UNKNOWN | 0xF7C30001 | 3150 status=0 |
| 3153 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xFC | 0xF/0x0 | UNKNOWN | 0x810B | 3155 status=0 |
| 3207 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x0 | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3209 status=0 |
| 3214 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x0 | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3216 status=0 |
| 3219 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x0 | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3222 status=0 |
| 3225 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xC | 0xF/0x0 | UNKNOWN | 0x0 | 3227 status=0 |
| 3230 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x0 | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3232 status=0 |
| 3235 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x34 | 0xF/0x0 | UNKNOWN | 0x80 | 3237 status=0 |
| 3240 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x8 | 0xF/0x0 | UNKNOWN | 0x8050104 | 3242 status=0 |
| 3246 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x80 | 0xF/0x0 | UNKNOWN | 0x2E010 | 3250 status=0 |
| 3253 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x8 | 0xF/0x0 | UNKNOWN | 0x8050104 | 3255 status=0 |
| 3258 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x100 | 0xF/0x0 | UNKNOWN | 0x1081000B | 3260 status=0 |
| 3263 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x8 | 0xF/0x0 | UNKNOWN | 0x8050104 | 3265 status=0 |
| 3268 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x108 | 0xF/0x0 | UNKNOWN | 0x11010018 | 3270 status=0 |
| 3274 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x8 | 0xF/0x0 | UNKNOWN | 0x8050104 | 3276 status=0 |
| 3279 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x110 | 0xF/0x0 | UNKNOWN | 0x1281001E | 3281 status=0 |
| 3286 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xC | 0xF/0x0 | UNKNOWN | 0x0 | 3288 status=0 |
| 3291 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x128 | 0xF/0x0 | UNKNOWN | 0x2001000E | 3293 status=0 |
| 3296 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x2C | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3299 status=0 |
| 3302 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x2C | 0xF/0x0 | UNKNOWN | 0x976717A0 | 3304 status=0 |
| 3307 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xFC | 0xF/0x0 | UNKNOWN | 0x810B | 3309 status=0 |
| 3312 | 8.277 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xFC | 0x3/0x0 | 0x800B | UNKNOWN | 3314 status=0 |
| 3320 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xF8 | 0xF/0x0 | UNKNOWN | 0xF7C30001 | 3322 status=0 |
| 3325 | 8.277 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xFC | 0xF/0x0 | UNKNOWN | 0xB | 3327 status=0 |
| 3330 | 8.277 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xFC | 0x3/0x0 | 0x8 | UNKNOWN | 3332 status=0 |
| 8594 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xFC | 0xF/0x0 | UNKNOWN | 0x8 | 8596 status=0 |
| 8599 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x10 | 0xF/0x0 | 0x6C1FF000 | UNKNOWN | 8601 status=0 |
| 8604 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x14 | 0xF/0x0 | 0x0 | UNKNOWN | 8606 status=0 |
| 8609 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x18 | 0xF/0x0 | 0x0 | UNKNOWN | 8611 status=0 |
| 8614 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x1C | 0xF/0x0 | 0x0 | UNKNOWN | 8617 status=0 |
| 8620 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x20 | 0xF/0x0 | 0x0 | UNKNOWN | 8622 status=0 |
| 8625 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x24 | 0xF/0x0 | 0x0 | UNKNOWN | 8627 status=0 |
| 8630 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x30 | 0xF/0x0 | 0x0 | UNKNOWN | 8634 status=0 |
| 8637 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x3C | 0x1/0x0 | 0x0 | UNKNOWN | 8639 status=0 |
| 8642 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xC | 0x1/0x0 | 0x0 | UNKNOWN | 8644 status=0 |
| 8648 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x4 | 0x3/0x0 | 0x400 | UNKNOWN | 8650 status=0 |
| 8653 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x88 | 0x3/0x0 | 0x1137 | UNKNOWN | 8655 status=0 |
| 8658 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x90 | 0x3/0x0 | 0x42 | UNKNOWN | 8660 status=0 |
| 8665 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xB0 | 0x3/0x0 | 0x2 | UNKNOWN | 8667 status=0 |
| 8671 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x10C | 0xF/0x0 | 0x0 | UNKNOWN | 8673 status=0 |
| 8676 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x118 | 0xF/0x0 | UNKNOWN | 0xF | 8678 status=0 |
| 8681 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x11C | 0xF/0x0 | UNKNOWN | 0x28 | 8683 status=0 |
| 8686 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x118 | 0xF/0x0 | 0xF | UNKNOWN | 8688 status=0 |
| 8691 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x11C | 0xF/0x0 | 0x28 | UNKNOWN | 8693 status=0 |
| 8696 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xA8 | 0x3/0x0 | 0x0 | UNKNOWN | 8698 status=0 |
| 8702 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x4 | 0xF/0x0 | UNKNOWN | 0x180400 | 8704 status=0 |
| 8709 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x4 | 0x3/0x0 | 0x406 | UNKNOWN | 8711 status=0 |
| 8714 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x4 | 0xC/0x0 | 0xF9000000 | UNKNOWN | 8716 status=0 |
| 8719 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0x4 | 0xF/0x0 | UNKNOWN | 0x180406 | 8721 status=0 |
| 8725 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x4 | 0x3/0x0 | 0x406 | UNKNOWN | 8727 status=0 |
| 8730 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xE0 | 0xF/0x0 | UNKNOWN | 0x80F805 | 8732 status=0 |
| 8737 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xE0 | 0xC/0x0 | 0x800000 | UNKNOWN | 8739 status=0 |
| 8742 | 8.314 sec | before_disconnect | CfgRd0 | 001:00.0 | 0xE0 | 0xF/0x0 | UNKNOWN | 0x80F805 | 8744 status=0 |
| 8748 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xE4 | 0xF/0x0 | 0x6850040 | UNKNOWN | 8750 status=0 |
| 8753 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xE8 | 0xF/0x0 | 0x0 | UNKNOWN | 8755 status=0 |
| 8758 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xEC | 0x3/0x0 | 0x0 | UNKNOWN | 8760 status=0 |
| 8763 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0xE0 | 0xC/0x0 | 0x810000 | UNKNOWN | 8765 status=0 |
| 9915 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x90 | 0x3/0x0 | 0x40 | UNKNOWN | 9918 status=0 |
| 10354 | 8.314 sec | before_disconnect | CfgWr0 | 001:00.0 | 0x90 | 0x3/0x0 | 0x42 | UNKNOWN | 10358 status=0 |
| 225043 | 9.512 sec | disconnect_interval | CfgRd0 | 001:00.0 | 0x200 | 0xF/0x0 | UNKNOWN | UNKNOWN | NONE_OBSERVED |
| 225048 | 9.512 sec | disconnect_interval | CfgRd0 | 001:00.0 | 0x200 | 0xF/0x0 | UNKNOWN | UNKNOWN | NONE_OBSERVED |

## 限制

- hardware snapshot or writes taking effect
- protocol timeout or complete transaction correctness
- post-reconnect SDE initialization beyond capture end
- vendor register decode
- same BDF implies same device across MUX switch
