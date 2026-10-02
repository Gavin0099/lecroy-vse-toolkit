# PCIe-B2f：Observed Snapshot Diff 契約

只比較同一 config log／layout reference 生成的 B2e snapshots；重新生成核對。
按 offset/width 對照，read 與 write intent 各自比較；只在同 BDF／同 connection
epoch 且兩值都已知時說 OBSERVED_VALUE_CHANGED／SAME_OBSERVED_VALUE。
缺值是 EVIDENCE_GAP；跨 epoch 是 NOT_COMPARABLE_DEVICE_EPOCH，不叫 register
消失、歸零或新 device 初始化失敗。變化不作產品 PASS/FAIL、根因或完整硬體 diff。

驗收：同 epoch 真的 read／intent 變化、unknown 不補 0、跨 epoch、篡改／混來源拒絕、
真實 MUX before/after 重播兩次一致。
