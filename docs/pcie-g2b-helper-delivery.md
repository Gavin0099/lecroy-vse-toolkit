# B2b 所需的既有 G2b helper

2026-10-02 獨立依賴交付。保留 vendor 常數映射、BDF formatter 與 historical
nearest-preceding candidate association；不把候選配對當 config read return。
B2b 只沿用 type/BDF helpers，另有自己的 config completion retirement。

六個原 fixture tests 核對 vendor code / 欄位形狀、key reuse、orphan、ordering、
不宣稱 timeout 及拒絕覆寫。主線 clean-slice suite 共 50 tests PASS。
兩次 CLI replay 的 roles / association / orphan JSON 與已保留 hang 證據逐位元組相同。

型別定義來源與 hash 在 script 常數註解；GUI_CONFIRMED 表示該 code 曾在
歷史 1350 capture 核對，不表示每個新 packet 都經 GUI 核對。
沒有交付 G1/G2 extractor、完整 transaction completeness、timeout 或根因。

2026-10-02 PR6 review repair: BDF bus/device components now use uppercase hex,
retaining repository padding (three bus digits, two device digits, no domain).
Literal requester/device ID 0x1F58 renders `01F:0B.0`; 0xFFFF renders `0FF:1F.7`.
The existing 0x0100 sample remains `001:00.0`. This corrects display identity;
request association keys still use numeric RequesterId/Tag and epochs are unchanged.
