# PCIe-B2a：Register Field Probe 驗收

2026-09-30：PASS，限本機 PETracer 13.26 Build 43 BETA、既有轉換後 non-Flit capture。
本地完成，沒有 commit／push／PR／merge。

## 真實 probe 結果

兩次 COM 均 DONE 且正常退出；704 TLP callbacks 與既有 G2a 相符。
333 個 config request／completion 記錄逐欄對照既有 packet、time、channel、
RequesterId、Tag、CompleterId、status；原始 VSE 輸出兩次位元組一致。

| 欄位 | 本次確立的意思與證據 |
| --- | --- |
| Register | Byte offset。所有 61 個 config request 與原始 frame header 的 address bits 一致；225043、225048 = 0x200，與既有問答所引用 GUI 樣本一致。不得再乘 4。 |
| RegisterData | Payload 的 little-endian DWORD；29 CfgWr、30 CplD 的 59 個值與 decoder payload 相符；當時 raw frame 只核對第一個 payload byte。3312 = 0x800B，payload `0B800000`；3150 = 0xF7C30001，payload `0100C3F7`。 |
| FirstDwBe / LastDwBe | Header 的 first／last DWORD byte mask。3312 為 0x3／0x0；只表示 byte 0、1 被 request 選取，不宣告其他 bytes 被寫入。 |
| CfgRd data | 32 個 request 沒有 payload／RegisterData；returned value 必須來自關聯的成功 CplD。 |
| PayloadLength | Bytes，與保留的 payload prefix 長度相符。非 config 的 CplD 不因型別就當 config data。 |

16-byte frame prefix 採本次觀察到的 FB／sequence／3-DW header 形式核對。
不支持此 layout 的 framing 會拒絕；沒有宣告完整 frame、所有 PCIe 版本或 flit 支持。
手冊 PDF 第 25–26 頁及 vendor example 只提供 probe 欄位來源，實際語意依上述 probe。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2a_register_fields.py -v`：7 tests PASS。
- 反例包含 offset 乘除 4、mask／device mismatch、endian mismatch、read request 補值、
  未完整輸出、metadata 不符與不支持的 framing。
- `artifacts/evidence/pcie-b2a-hang-20260930/verification.json` 保留 script／manual hash、
  真實兩次重播與完整性結果。原檔及舊副本只雜湊，轉換副本保持 read-only。
- 正式欄位產物 `verified1/fields.json`；`verified2` 只有 COM run 身分不同，欄位內容一致。

下一階段 B2b 建立逐筆 config log；本 gate 不解碼 register 意義、不判定初始化成功。

## 2026-10-02 review repair: independent raw DWORD

PR5 review exposed that the 16-byte frame prefix covered only the first payload
byte. The 2026-09-30 result above is historical decoder consistency evidence,
not full raw-DWORD proof. It is retained unchanged.

Two fresh COM runs use the same read-only converted trace and a new 19-byte probe.
Both finish DONE, exit normally, and produce byte-identical raw output. All 333
rows match the old scalar/payload fields; each old frame prefix matches the new
prefix. The 59 DWORDs now independently match raw frame bytes 15..18. No missing
raw bytes were synthesized. Source/old copies are hash-only; protected identities
and analysis-copy read-only state remain unchanged.

Current evidence: `artifacts/evidence/pcie-b2a-raw-dword-20261002/verification.json`,
`length-verified1/fields.json` and `length-verified2/fields.json`; 11 focused tests and
77 clean-slice tests PASS at this revision, with log hash in verification.
The CLI rejects short legacy proof for new qualification. Downstream historical
replays still use their preserved inputs; the equality bridge above validates
their decoded values for this capture, without changing their source hashes.

Scope remains PETracer 13.26 / converted non-Flit capture only. This does not
prove register writes applied, product ASPM policy, or hang/BSOD causality.

Review also reproduced decoded payload lengths 0/1 bypassing the raw DWORD gate.
The verifier now rejects a length inconsistent with the raw TLP format/length
header before comparing bytes. Fresh raw outputs are replayed through this gate;
the same 59 RegisterData DWORDs pass.
