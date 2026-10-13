# U01 offline fixture oracles

2026-10-13。預期值來自既有 U01 slice 驗收、S01 已接受契約與已閱讀 installed LC-04 章節。以下都是手寫合成 callback／counter，沒有真實 runtime qualification。

| Case | 獨立輸入與預期 |
| --- | --- |
| Selection flags | LC-04 PDF168 完成旗標 default=1、0 表未完成；PDF170 bad-CRC default 不送、顯式 0／1 分開；PDF152／157／161 的 named level／channel／event primitives |
| Payload | LC-04 PDF19／20 的 Index／Level／Channel／Speed／TraceEvent／Time；PDF89 的 Completed 僅 transfer 使用；非 transfer 固定 -1 sentinel |
| Count denominators | 手寫 visited=17、selected=2、emitted=2、indices=10／20；預期三種 count 分開，不能當 packet 數 |
| Empty selection | 手寫 visited=17、selected=emitted=0；預期空 row、bounds=null、event unknown/count=0、bad-CRC unknown；不能改成不存在 |
| Transfer | 手寫 level-local row index=10、Completed=1 或 0；顯式 selector 不符則拒絕；不產生 packet reference 或覆蓋 PASS |
| Partial sample | 手寫 selected=600、exported=512、visited=900；預期 sample_truncated=true、manifest extraction=partial |
| Missing/duplicate end | 對帳契約要求恰好一個 end 與 finished marker；缺 summary 或重複 end、end 後有 row 均拒絕 |
| Identity and preservation | 三個 integrity boolean 各自要求 true；0／1／文字不當 boolean；錯 trace/script hash、旗標、namespace、script path 或 extra verdict 拒絕 |
| Numeric shape | JSON count/context 用整數，不能把 bool／string／fraction 自動轉整數；秒／ns 非負且 ns<1e9；completion 不適用用 -1 |
| Output boundary | 既有目錄不覆寫，非法 range 不先建立輸出；assess 只讀 saved JSON、stdout 回傳，原輸入 bytes 不變 |

Python 測試的 numeric fixtures 和預期 tuples 手寫；沒有呼叫 production 產生 expected counters。Script hashes 是生成實際檔案的身分檢查，不是獨立協定 oracle。C# replay 只呼叫 managed sink 方法，不呼叫 `U01Host.Run` 或任何 COM constructor。這些測試尚不能证明 script 在本機 VSE 可解析，或某種 trace 事件真的被保留。
