# PCIe-B2a：Register 欄位 probe 契約

僅讀取既有 13.26 轉換副本；原檔及早期未轉換副本只做完整性檢查。
COM 執行仍使用已驗證的 `com_run_vse.py`，不更改 analyzer 設定。

## 待驗證

- `in.Register` 與 packet 中 config address／既有 GUI Register 0x200 樣本
  比較，確立 byte offset 或 DW index；手冊文字本身不當作 probe 結果。
- `in.RegisterData` 在 CfgWr 與 CplD 與原 payload bytes 比較，確立 endian。
- `FirstDwBe`、`LastDwBe` 保留原始 mask，與 frame header bytes 比較。
- CfgRd 沒有 payload 不得把 RegisterData 的數值當 read result。
- Request/Completion 以 packet、RequesterId、Tag、channel 與 status 核對；
  尚未配對的 CplD 不當作 config read result，沒有 completion 不補值。

## 來源

本機 `PETracerVSEManual.pdf` PDF 第 25–26 頁（印刷頁 20–21）列出
Register、Address、First/LastDwBe、RegisterData、Frame。
本機 `Examples/examp_tlp_data.inc` 顯示 `GetNBits` / `NextNBits(8)` 逐 byte
讀 payload。手冊可能有誤，欄位語意需以真實 packet probe 核對。

## 驗收與限制

Probe 發出全 trace 的 config requests 與 completions，保留最多 16 bytes
payload 與 19 bytes frame prefix；宣告 prefix，不冒稱完整 frame。
所有 TLP callback 計數與既有 704-row G2a log 對照；保留 NA，不補 0。
驗收需要真實 CfgRd、CfgWr 與成功 CplD；逐 byte cross-check 不符先查明。
輸入 hash、size、mtime 及 analysis-copy read-only 狀態必須保持。
先完成此 gate 才建 B2b config access log；不解碼 vendor register 或根因。

## 2026-10-02 full raw DWORD gate

The fresh probe records 19 raw frame bytes. On the qualified FB/sequence/3-DW
layout, raw bytes 15..18 independently verify the first payload DWORD. Coupled
errors in Payload and RegisterData cannot substitute for this proof. New CLI
qualification requires all raw bytes needed for the first DWORD; historical
16-byte inputs can only pass the library consistency checks for legacy replay.
`payload_dwords_checked` on a historical artifact describes decoder consistency,
not independent full raw-DWORD validation. New CLI output labels its basis.

Payload length is first cross-checked with raw TLP DW0: format distinguishes data
from no-data, and the 10-bit length supplies DWORD count (encoded zero is 1024
for data formats). Primary implementation reference: [cocotbext-pcie TLP decoder,
commit 6e6081d](https://github.com/alexforencich/cocotbext-pcie/blob/6e6081d441debac7512b25fd4b7bc92f137e95a3/cocotbext/pcie/core/tlp.py#L505).
This is a layout reference, not complete PCIe spec/product verification.
Decoded lengths 0 or 1 cannot bypass a raw one-DWORD data header.
