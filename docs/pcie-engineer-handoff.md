# PCIe 測試背景交接包 — P1 / P2 / P3

更新：2026-09-12。用途是一次確認測試背景，不是診斷報告或 F5 review build。

## 現在已知什麼

D1e 已完成：同一最小 extractor 在 1350 / 1335 兩份不同 trace 取得前五筆 TLP，GUI 核對與關閉後完整性通過。這不代表全 trace extraction、capture health、測試 PASS 或故障診斷成立。1329-Fail 尚未執行 extraction。

另附 [1350 單 trace inspection Markdown](../artifacts/reports/pcie-inspection-1350-20260912/report.md) 與 [HTML](../artifacts/reports/pcie-inspection-1350-20260912/report.html)，提供 presentation 試閱。這不是 PASS/FAIL triage；Extraction 僅標示前五筆 TLP 範圍，ground truth 仍 UNKNOWN。F0e 工程師回饋尚未取得。

## P1 — Trace manifest

來源目錄（capture 留在本機，不放 Git、不隨文件散布）：

`C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767`

本輪以 Get-FileHash SHA256 重算全部八份檔案，均與既有 [source inventory](../samples/pcie/README.md) 相符；hash 前後大小與 UTC mtime 不變。這是來源身份確認，不是八份都跑過 runtime。

| 檔案 | Bytes | SHA-256 | Extraction |
| --- | ---: | --- | --- |
| Disable ASPM--Insert SD7-hang-2.pex | 113113593 | `7147529BC0DAAD709085874DEEC64C5D5E8F28CE9F6CC5BBC52BADAF0E287479` | BLOCKED before load: v12.36 format-update prompt; extractor NOT RUN |
| Disable ASPM--Insert SD7-hang.pex | 126339103 | `F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6` | BLOCKED at load dialog; exact message not recorded; extractor NOT RUN |
| G3-Power on wwth SD7-1329.pex | 406998300 | `66DAB50A6100FED0739445C8C7BB54E80E7D4D3D042D54D4064FD3BD9AEF77E0` | UNKNOWN / NOT RUN |
| G3-Power on wwthouut SD7-1328.pex | 121698585 | `3A9DB43C017AD6269E2EB77D5060F3DC7818DD6B29B744217727175952D0C504` | UNKNOWN / NOT RUN |
| S0-Insert SD7-1334.pex | 354152683 | `86F2CCF6BCFFC51A1CCADCB4C8D49EF7EE6C3E92DEE8D329CCB2008027EE665C` | UNKNOWN / NOT RUN |
| S0-Remove SD7-1329-Fail.pex | 150552514 | `D704C0052D0D3635FD95F041A86A67ACB6598E6B1371EF23180E6EDBA3BA25D5` | UNKNOWN / NOT RUN |
| S0-Remove SD7-1335.pex | 107086178 | `9C90FB3351B5D9260D6A966463A9A7DEE21595B5094A45AF391E7ED598482E81` | PASS — first 5 TLPs only |
| S0-Remove SD7-1350.pex | 105224486 | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` | PASS — first 5 TLPs only |

## P2 — Ground-truth status matrix

CONFIRMED 需要測試人員或可追溯測試紀錄確認結果及背景；目前沒有任何一份符合。FILENAME_HINT_ONLY 只表示名字含 Fail/hang，實際 outcome 仍 UNKNOWN。未標 Fail 的檔案不自動視為正常。

| Trace（檔名縮寫） | GUI sample check | Ground-truth status | Confirmed outcome |
| --- | --- | --- | --- |
| Disable ASPM--Insert SD7-hang-2 | BLOCKED before load: v12.36 format-update prompt | FILENAME_HINT_ONLY | UNKNOWN |
| Disable ASPM--Insert SD7-hang | BLOCKED at load dialog; exact message not recorded | FILENAME_HINT_ONLY | UNKNOWN |
| G3-Power on wwth SD7-1329 | UNKNOWN / NOT RUN | UNKNOWN | UNKNOWN |
| G3-Power on wwthouut SD7-1328 | UNKNOWN / NOT RUN | UNKNOWN | UNKNOWN |
| S0-Insert SD7-1334 | UNKNOWN / NOT RUN | UNKNOWN | UNKNOWN |
| S0-Remove SD7-1329-Fail | UNKNOWN / NOT RUN | FILENAME_HINT_ONLY | UNKNOWN |
| S0-Remove SD7-1335 | PASS — 5 TLPs | UNKNOWN | UNKNOWN |
| S0-Remove SD7-1350 | PASS — 5 TLPs | UNKNOWN | UNKNOWN |

## P3 — 工程師只需確認這五件事

1. 1335、1350 哪份是正常紀錄？或兩份是不同狀況？請逐份說明。
2. 1329-Fail 當時實際看到什麼異常？Fail 命名是否確實代表該異常？
3. 當時操作步驟是什麼，操作後觀察哪個裝置／功能？
4. 正常應該發生什麼，實際正常／異常觀察分別是什麼？
5. 三份是否相同測試條件？請註明已知的硬體／韌體／ASPM／操作差異及紀錄提供者或來源。

可直接填寫（不知道可保留 UNKNOWN；不需要先提供 root cause 或 API）：

```text
確認者／測試紀錄來源：
正常 trace 完整檔名：
正常實際現象：
異常 trace 完整檔名：
異常實際現象：
操作步驟：
預期結果：
相同測試條件／已知差異：
希望工具回答的一個問題：
```

### 已知證據與回看入口

- 1350：[GUI 五筆核對截圖](../artifacts/evidence/pcie-staircase-20260912/d1-gui-crosscheck.png)、[原始輸出](../artifacts/evidence/pcie-staircase-20260912/d1-vendor-saved-output.log.txt)、[關閉畫面](../artifacts/evidence/pcie-staircase-20260912/final-closed.png)。Packet 1944516、1944517、1944519、1944521、1944523。
- 1335：[已載入畫面](../artifacts/evidence/pcie-d1e-20260912/b-ready.png)、[執行結果截圖](../artifacts/evidence/pcie-d1e-20260912/b-extraction-result.png)、[原始輸出](../artifacts/evidence/pcie-d1e-20260912/b-vendor-output.log.txt)。Packet 2000010、2000011、2000013、2000015、2000017。新 GUI 核對觀察記錄見 [D1e closure](pcie-staircase-evidence.md#d1e-final-closure--2026-09-12)。新截圖帶其他應用程式縮圖，未納入交接包；不把舊 Go-to dialog 圖當核對證據。
- 1329-Fail：目前只有檔案身份與檔名提示，沒有 GUI／extraction 證據。

回看時只開受保護的 working copy；PETracer 的 Search → Go to Packet 輸入上述 index。原始 trace 不直接開啟或儲存；操作前後核對 SHA-256。`Errors detected!` 與成功 extraction 均不是產品測試結果。

P1/P2/P3 已整理成可本機交付的 inventory、狀態表與交接包；交接包尚未送出，E1a 尚未通過。依 owner decision，P4 為 **DEFERRED / LEGACY_FORMAT_COMPATIBILITY**，不阻擋 E1a。兩次開啟嘗試中，第一份 trace 顯示版本轉換提示；第二份出現模態視窗但內容未成功記錄。兩次都未執行 extractor，另四份未嘗試。提示證據：[first legacy format-update dialog](../artifacts/evidence/pcie-p4-20260912/legacy-format-update-prompt.png)，僅對應第一份。提示稱檔案由 LeCroy PETracer 12.36 Build 19 修改，更新後可能無法被較舊軟體讀取。本輪取消轉換，source 與六份唯讀 pristine copy hash 保持相同；沒有任何舊格式相容性結論。

只有當工程師確認 E1a 所需的 PASS/FAIL trace 必須使用這批 legacy-format 檔案，才重新啟動獨立的 **P4a — Legacy Trace Conversion Qualification**。屆時來源保持唯讀，只對額外可丟棄副本轉換並記錄轉換前／後 hash、PETracer 提示、轉換後載入與 extractor 結果。轉換後 hash 不證明與原始檔 bit-equivalent，也不可取代原始 source identity。P4a 目前 DEFERRED，沒有執行。

## F0e — Single-trace report review prompts

Preview: [Markdown](../artifacts/reports/pcie-inspection-1350-20260912/report.md) / [HTML](../artifacts/reports/pcie-inspection-1350-20260912/report.html). Please review presentation only; this sample carries no normal/abnormal label.

1. Can you quickly locate the trace identity, the five checked TLPs and their GUI evidence?
2. Which displayed fields help you inspect a trace, and which can be removed?
3. Is the GUI-only packet context enough, or what neighboring packet details would you need?
4. Is the separation between coarse extractor time and GUI timestamp clear?
5. What single piece of context is missing before this report would be useful during debugging?

F0e feedback is pending. This review does not request ground truth through the report itself; the five P3 questions above remain the E1a source for ground-truth qualification.
