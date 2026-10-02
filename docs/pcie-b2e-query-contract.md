# PCIe-B2e：Snapshot Query 契約

輸入 config log、已來源化 layout reference、BDF routing ID 與 packet cut。
重新建立同 epoch 的 B2d read／write-intent views，capability map 只用 cut 前已回覆
的 headers。輸出每個 register 的 last read value、last requested value、bytes／
證據 packet；缺任何 byte 的整體值為 UNKNOWN，已知 bytes 仍保留。
Read 後有較晚 write 時標示 `read_has_later_write`，不把舊 read 當當前硬體值。

預設列標準 registers、已支持的 capability registers、cut 前該 epoch 存取過的
DWORDs。也可明確查 raw offset/width（1/2/4 bytes），不因 query 就替未知
offset 命名。沒有存取的 new SDE register 保持 UNKNOWN。
驗證 query boundary、partial bytes、later-write marker、未知值及 epoch isolation。

Named register widths: CapabilityPointer=1 byte; Command/LinkControl/LinkStatus/
PMCSR=2 bytes; DWORD fields=4 bytes. Raw accessed DWORDs remain separate when
a named field has smaller width. Reserved bytes cannot contribute to a named
field value or its later-write marker.
