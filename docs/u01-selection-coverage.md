# U01 — USB selection / coverage probe

2026-10-13。S01 review 未發現阻擋問題。最新使用者已放行唯讀 runtime 及逐片 review 後續作，不再逐片確認。U01 的七種模式已完成兩次語意一致的受控執行；review 通過指定 trace／設定的 selection transport 範圍，後續已接 U02／U03。特殊事件完整 coverage 仍未資格化。

工程師問題是「目前輸出沒有某種事件，是沒有遇到，還是 selection 沒有選進來？」預期成果是明列設定、level-local range、callback／輸出對帳與尚未證明的覆蓋。此片不判 root cause 或協定 PASS／FAIL。

## 已完成的可審查實作

- [離線準備與結果驗證](../tools/u01_selection.py) 產生七份有 SHA-256 的 VSE 腳本、固定 plan；驗證 saved host payload，產生獨立 S01 sidecar manifest。
- [執行器](../tools/run-u01-selection.ps1) 預設只做 preflight，不啟動 COM；只有明確 `-Execute` 才用新建的唯讀副本執行。
- [USB host](../tools/u01-selection-host.cs) 使用既有 M2 的 USB event IID／dispatch shape；檢查單一 end marker、finished callback、整數 payload、最多 512 筆樣本。沒有修改既有 host 或 extractor。
- [Python tests](../tests/u01/test_u01_selection.py) 和 [managed callback replay](../tests/u01/test-u01-host.ps1) 不啟動 COM 或 LeCroy；檢查手寫 payload、負面案例、manifest 與 runner 語法。

| Selection | 唯一 level | 與其他設定相同時的差異 |
| --- | --- | --- |
| packet-default | `_PKT` | 不呼叫 bad-CRC primitive |
| packet-crc-off | `_PKT` | `SendPktsWithBadCRC(0)` |
| packet-crc-on | `_PKT` | `SendPktsWithBadCRC(1)` |
| transaction-all | `_TRA` | `SendAllTraceEvents()` |
| transfer-default | `_XFER` | `SendTransfer(_ANY, _ANY, _ANY)` |
| transfer-complete | `_XFER` | completed=1、only_with_errors=0 |
| transfer-incomplete | `_XFER` | completed=0、only_with_errors=0 |

依據為已安裝 LC-04 Manual 9.12（July 2025，Suite 10.13+）PDF19／20／89／152／157／161／168／170，以及 LC-10／11 的 level 範例。文件內舊敘述、API 支援與實際 dispatch 分開驗證，使用 named constants，不以文件 enum 數字取代本機解析。

每個 profile 使用 `SendAllChannels()` 與 `SendLevelOnly()`。Index guard 在 callback 送達後才套用；requested range 是各 level 的 event index，transaction／transfer index 不當成 packet number。範圍內 callback 計數、輸出樣本筆數與全遍歷 callback 分別保存。最多輸出 512 筆，超過則 extraction=partial。Delivered bounds 僅為已輸出資料的 min/max，不宣稱 native effective capture range。

## 執行安全與驗收上限

Plan、來源 trace 與每份 script 的 hash 必須相符。來源保持原屬性，每次 run 新建一份唯讀 working copy；source 與 working copy 的 SHA-256、size、mtime、readonly 逐次核對，任何變動即停止後續 profile。拒絕覆寫既有 evidence／output，沒有 Save、capture 或硬體命令。原始輸入、副本與結果各自保存。

Host payload 對帳通過只表示輸出 transport 自洽。零筆 callback 的 manifest 保留 state=unknown，不能變成 absence；retention 維持 unknown。mode、雙向、capture 起訖及 epoch 不由 trace 檔名、少量 callback、或 `SendAllChannels` 推定。新 manifest 不回寫舊 evidence，歷史 DEMO PASS 維持原適用範圍。

bad-CRC 實際覆蓋需要獨立已知 packet 樣本；flags 對照有差異也不能單靠差集判為 CRC error。未完成 transfer 的 selector 與 `in.Completed` 可做相符性查核，但需要已知樣本才能宣稱該類 coverage 資格化。空樣本、新模式的成功執行或相同 counts 均不足以資格化。所有離線 assessment 固定 `qualification=NOT_EVALUATED`；W1–W5、舊 USB scoring／report 不變。

## 準備完成的實際計畫

[Prepared plan](../artifacts/evidence/s01-review-u01-20261013/prepared/plan.json) 使用既有 USB FAIL 角色輸入的 SHA-256 `a5568248d1c3d04f3cc16d6d3649f1303be0d15ffa1a734e2057d73564836cae`，104,136,704 bytes。此 FAIL 是歷史角色，不是本輪判定。範圍為 0–200 inclusive、每個 level 各自計數。

[Preflight](../artifacts/evidence/s01-review-u01-20261013/preflight/preflight.json) 核對來源與腳本 hash、已安裝 executable 10.40.0.6309、manual 與 constants 身分。這是檔案查核，沒有啟動 COM／LeCroy；不證明 VSE syntax 或 runtime 可用。

尚未確認這份 trace 在指定 window 包含獨立已知 bad-CRC／incomplete 樣本。故可先驗新模式的語法、dispatch 與對帳，不能宣稱 U01 已完整資格化。

目前為 14 項 Python tests、8 組 managed callback replay、2 組 activation recovery、C# 編譯及 PowerShell 5.1 語法檢查。Native run 發現原 v1／v2 模板的負值寫法沒有進到執行；v3 改用 `NOT_APPLICABLE` wire token，host 明示轉為內部 -1，不轉成 false/0。舊模板與失敗 run 保存，不接受為新的 runtime plan。另修正新 COM server 與前一 server 關閉的 RPC race，只在尚未開 trace 的 activation 階段有限重試；已開始的 probe 不自動重播。

## 已放行並完成的 runtime

最新授權已解除目前唯讀 probe 的等待；硬體操作、commit／push／merge 與 checkout 搬動仍排除。使用 [v3 plan](../artifacts/evidence/serial-slices-20261013/u01-prepared-r3/plan.json) 的兩次成功 run 為 `u01-run-r3a` 與 `u01-run-r3c`；[review evidence](../artifacts/evidence/serial-slices-20261013/u01-review.json) 逐筆比較全部七種語意輸出。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/run-u01-selection.ps1 `
  -TracePath 'dp1 hub detect SSD fail-2.usb' `
  -PlanDirectory artifacts/evidence/serial-slices-20261013/u01-prepared-r3 `
  -Output '<NEW output directory>' `
  -Python 'C:\Users\reiko\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -Execute
```

| Mode | 全遍歷 callback | 0–200 window callback／輸出 |
| --- | ---: | ---: |
| packet-default／crc-off | 3,174,680 | 202／202 |
| packet-crc-on | 3,174,690 | 202／202 |
| transaction-all | 300 | 201／201 |
| transfer-default／complete | 138 | 138／138 |
| transfer-incomplete | 0 | 0／0 |

CRC flag 開啟多出 10 個 window 外 callback，尚未以獨立已知 bad-CRC packet 資格化；incomplete 空樣本也不證明不存在。14 份成功 run 的 working copies 與來源完整性通過。Count 是 callback，不能單靠 index window 長度推成 packet 數。
