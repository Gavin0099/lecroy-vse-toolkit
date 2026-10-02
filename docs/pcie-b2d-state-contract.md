# PCIe-B2d：Last observed config state 契約

本版「state」指 trace 中最後一次可觀察的 read return 及 write request 意圖，
不是硬體快照。每個 BDF、connection epoch、byte 分開維護。
Read 在成功 Completion packet 才可用；write 在 request packet 可觀察到意圖，
只更新 FirstDwBe 選中的 bytes。不得把 write intent 合併成已生效 read state，
包括 W1C/status bits；每個 byte 保留自己的證據 packet／access ID。
UNKNOWN 以 null 表示，0 是已觀察的數值，不可混用。

Disconnect interval 與 after reconnect 不沿用舊裝置。Completion 跨 epoch
不放進新 epoch 的 state。查詢未觀察過的 byte 仍為 UNKNOWN。
後續 B2e 可查 last read 與 last requested value，標示 read 後是否有更晚 write；
B2f 比較時不能把跨裝置 epoch 的 UNKNOWN 說成 register 變 0。

驗收：Completion 時點、partial write、未觀察 bytes、零值、跨 epoch、真實重播。


Owner review 補強：相同 BDF／offset／VID-DID 不建立 identity continuity。
目前沒有 continuity-proof contract 或例外路徑，state 一律按 epoch 隔離。
Regression 同時驗證 read、write intent 與 capability 名稱不跨 epoch。
