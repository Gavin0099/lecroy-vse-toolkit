# I01／I02：新觀測進入既有報告

兩片都完成本地驗收。工程師現在能在報告中看到原生欄位、packet 引用、來源 hash、
抽樣限制與缺少的證據；尚未建立新的 compliance 或 root-cause 結論。

## I01：PCIe P03 source block

[實作](../tools/pcie_protocol_appendix.py)使用 W1–W5 的既有 renderer，新增獨立、具型別的
`pcie.protocol-appendix/v1` 區塊。JSON 將原 `pcie.observation-report/v1` model 放在 `base_report`，
附加資料位於 `protocol_appendix`；沒有修改 W1 timeline schema，也沒有解讀 opaque extensions。

Dependencies 來自 `C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit`，
commit `f417eecb340f56d09d6e4c0ca0b86f81e2977181`。執行前後檢查 clean checkout、Git blob 身分
及磁碟 SHA，處理正常 CRLF checkout filters；沒有搬動檔案。

新增124筆 P03 raw observations，JSON→MD／HTML 使用同一 model。原 Markdown byte prefix、
移除新增區塊後的原 HTML，以及完整 base model 均保持一致。W1 的 effective／expected UNKNOWN、
policy NOT_EVALUATED 保留；原有 milestone PASS 仍在其原範圍。

[PCIe HTML](<C:/Users/reiko/.codex/visualizations/2026/10/13/01a13339-798e-7020-8e39-ec838f3ed292/pcie-observations/report.html>)
／[JSON](<C:/Users/reiko/.codex/visualizations/2026/10/13/01a13339-798e-7020-8e39-ec838f3ed292/pcie-observations/report.json>)
／[Review](../artifacts/evidence/p03-serial-20261013/i01-review.json)。517個 JSON pointer links 已解析。

## I02：USB U02 source block

[實作](../tools/usb_report_appendix.py)沿用 `render-c5-html.ps1`，以歷史 C5 JSON 建立原報告，
另外加入 `usb.native-command-appendix/v1`。歷史 JSON、候選排名、source-integrity 與原 HTML 內容
都保留。新的 source block 只呈現128筆 LINK_CMD 樣本，綁定與 C5 FAIL trace 相同的 SHA。

先從 U02 原生 output 重算 observation，比對 saved observation；額外 extension、source mismatch、
raw value tampering 均拒絕。SS／SSP 保留為事件的 native speed 標籤，沒有推測 capture negotiated mode。
CRC5 仍是 vendor decoded raw field；沒有重算 CRC 或判定 Enumeration 成敗。

[USB HTML](../artifacts/evidence/p03-serial-20261013/usb-composed-report/report.html)
／[JSON](../artifacts/evidence/p03-serial-20261013/usb-composed-report/report.json)
／[Review](../artifacts/evidence/p03-serial-20261013/i02-review.json)。128個 packet source pointers 已解析。

## 驗收與限制

I01有8項測試，I02有6項測試；涵蓋 unknown／不適用、原結論保留、來源重播／pointer、
source mismatch、opaque verdict 拒絕、HTML escaping／offline resources 和唯一 anchors。
既有 W1–W5 harness 另跑，結果見 [本輪 verification](../artifacts/evidence/p03-serial-20261013/verification.json)。

這是本機 source-linked 報告，原 evidence 路徑需要保留；不是可任意搬移的 standalone package。
PCIe 原 W5 hyperlinks 需要 output 與 frozen checkout 同磁碟，因此報告置於 C:；新增 E: evidence
使用 offline file URI。沒有共用 USB／PCIe scoring 或 root-cause core。
