# USB / PCIe Trace Triage — local trial

Current desktop-index trial (2026-10-21): `USB-PCIe-Trace-Triage-Fast-20261021-r7.4.zip`.
Read [the dense-analysis guide](pcie-dense-analysis-usage.md) for disk-backed
TLP validation/association and separately stored native evidence arrays.
The previous r7.3 and r7.2 ZIPs remain frozen. The r7.2 20,000-TLP refusal is
superseded by r7.3 automatic disk-index routing; see the new guide for the
remaining explicit graph/model/disk budgets. Native 1 GiB+ capacity and full
analysis caching remain unqualified.
Extract the whole folder and run `USBTraceTriage.exe`.
The recovery update retries brief Windows access/sharing denials when reading
worker progress. Persistent denial or invalid receipts still stop publication.
Dense row/field/message exports batch at most 256 records per COM callback;
all records retain the original formatting/order and complete-tail validation.
Disk allowance checks replace per-row volume queries; resource ceilings remain.
Bounded row JSON encoding avoids per-field Python chunks while retaining the
canonical bytes; lazy nested completion sequences still stream to disk.
Association export reads joined records in capture order. At most 16
Completions are encoded in a bounded transaction record; larger fanout streams.
Desktop dense analysis keeps the complete SQLite rows/associations and canonical
fields/messages. Duplicate diagnostic row/role/association JSON and TSV are
generated on demand. See the dense-analysis guide for the offline export command.

Previous frozen baseline (preserved unchanged):
`USB-PCIe-Trace-Triage-Flow-20261020-r7.1.zip`.
SHA-256: `a694c0c4e7571a2cd4f61ccba65c0e38cd3bc1b2aed8bf98e6fc8e19e30f8263`.
The r7.1 ZIP and its internal documentation have not been replaced.
Older r3/r4/r6/r7 release notes are historical.

Local validation used PETracer 13.26.0.43 Beta and USB Protocol Suite 10.40 Build 6309.
USB Protocol Suite 10.50, other PETracer versions and other Windows machines remain
unverified; record the exact product and version instead of calling them all 10.50.
Historical r7.1 known-case timing was 132.3 s for PCIe import/analysis, 29.1 s for first navigation and
about 9–10 s for later navigation. These are separate measurements, not an end-to-end
time-saving result or a promised duration for new traces.

Extract the whole ZIP, then run `USBTraceTriage.exe`. Python 3.13.16 and the
pywin32 311 COM runtime are bundled; no developer Python, pip or Git is needed.
LeCroy's installed/licensed analyzer and COM registration are still required.
USB uses USB Protocol Suite; PCIe uses PCIe Protocol Suite / PETracer. An existing
PETracer session blocks PCIe operations; the tool does not take it over.

## Same workspace

Use **匯入 Trace**, Ctrl+O, or one-file drop. `.usb` selects the existing USB2 /
USB3 / PD pipeline. `.pex` selects PCIe extraction and its independent analysis.
The filename, PASS/FAIL label, failure timestamp and a baseline are not inputs
to PCIe candidate discovery. An accepted import clears previous candidates.

PCIe defaults to **流程階段與下一步**, displaying at most three scoped flow checks
under the current inspection policy. **包含較早流程** expands historical intervals;
**次要交易觀察** retains Packet candidates in capture order. Neither presentation
is a validated ranking of the three most likely faults or a root-cause probability.
The right pane contains observations, reasons, next checks, source evidence and
coverage. Unknown timestamps/channel/epoch remain unknown.

The first screen now shows findings and Coverage above the candidate details.
PCIe also shows the last source-supported stage and the next unverified step.
Per-direction L0 is a native observation, not device initialization or a fault
verdict. The Packet shown on the candidate navigation button remains that
candidate's target. **定位最後階段** navigates to the separately identified stage
Packet. In the default flow view, **定位階段證據** targets that flow's supported
milestone. These stage observations do not establish a fault.
Stage events, native Link/Split cross-checks and their source references are
available under **限制與來源** and in both report formats.
Orange **待覆核** means inspect this segment, not confirmed failure. Blue shows
the selection or main action; purple labels related evidence. Neutral PD flows
remain **一般流程**. Green names only the verified operation (for example TLP
subscription extraction), never a whole-trace PASS. Red operation errors are
explicitly labeled separately from protocol fault judgments.

Read **觀察到什麼 → 為什麼值得看 → 下一步核對** first. **展開關聯事件** opens
the saved context events; select one with the mouse or arrow keys, then use
**查看 … 的完整證據** to see the same source row. Coarse or unknown times are
labeled as event order, with no invented spacing or complete coverage band.
Browsing a neighboring event does not change the candidate's native navigation
target shown above the action button. All facts and reasons remain under
**限制與來源**. Small windows or long descriptions may require scrolling.

**在 PETracer 定位** opens/reuses the owned readonly copy and verifies the native
export's full file path, Packet, time and direction. It selects the Packet, then
invokes the named Search / Go to Selected Packet menu using UI Automation and
checks both selected and first-visible indices. Restored off-screen placement
still required system-menu Maximize during local qualification: automatic
multi-monitor recovery is not guaranteed. If the native window is not visible,
bring this tool's PETracer window to the main monitor and maximize it, then verify
the file and Packet. Do not manipulate an unrelated engineer session.
No fixed coordinates or keystrokes are encoded in the product menu path.
If the menu/readback is unavailable, use **複製 Packet** and Ctrl+G in PETracer.
**複製副本路徑** supplies the exact file. Complete any native dialog before retrying.
Each operation records its actual result and duration; readback is not a claim
that a human reviewed the packet. **結束定位工作** closes the owned trace and
waits up to 30 seconds for the native process to exit. Report exports remain available.

**匯出報告** saves PCIe HTML or Markdown from the same inspection model. The HTML
is self-contained; source references identify local evidence but do not upload
anything. Share the reports intentionally: they contain local paths and hashes.

## Coverage and recovery

The current PCIe pipeline subscribes to TLP / any TLP type / all channels. The
row probe has a 100,000,000-row safety cap; cap/partial/missing DONE is rejected.
The additional phase pass counts explicitly subscribed events and retains at
most 4096 LTSSM changes, 512 Link events, 256 speed/width changes and 16 samples
per DLLP class. A separate native transaction pass retains at most 8192 Config /
Completion records per Packet, Link and Split namespace. Caps and omitted
records are disclosed independently. Physical Link pairing, native Flow Graph
ignore-setting equivalence, ASPM policy and vendor register activation remain
unverified. DONE means script completion. `ScriptForDisplayOnly`
and display-filter effects are explicitly unqualified. Native packet count and
TLP count have different denominators. No candidates does not mean PCIe PASS.

The NFM LTSSM ignore mask is read from the native VSE and included in Coverage;
this does not establish equivalence with independently configured Flow Graph.
A second-stage native text export uses this import's first three candidates
and last supported stage: 16 preceding and 32 following indices, clamped to
the native range, overlapping windows merged, at most four windows. Only the
actually exported rows are evidence. Missing/filtered units and full-trace
coverage remain unknown. Partial detail exports retain the original analysis
with an explicit gap; changed source/hash/range is rejected. Read the rows under
**前後交易** and full provenance under **限制與來源** or in exported reports.

Cancellation waits for a safe boundary between native calls. During an active
call the UI says cancellation was requested, not completed. Timeout kills only
the owned Python worker; native cancellation stays unknown. The copy and logs
are retained. Check PETracer, save existing work, then restart the tool when the
native state is understood. The tool does not force-kill PETracer.

If readonly `OpenFile` fails, the importer tries the vendor `OpenFile2` format
update on a separate, writable `conversion-working.pex` in the job folder.
It closes that trace, seals the result readonly, and reopens a byte-verified
`display-working.pex` for acquisition. The original is never passed to either
native open method. Source integrity, conversion provenance and the final
display hash are checked before publishing candidates. Packet numbers refer
to the converted display file; an original-to-converted index map is not inferred.

Unavailable conversion APIs or failed updates retain the original open error
and conversion error. Manually update another copy in PETracer and import it
if automatic conversion fails. Cleanup is reported separately; an unsuccessful
open with no remaining native process is not a cleanup failure. Timeout and
unconfirmed native closure still block further work. Conversion compatibility
with other PETracer versions remains unqualified.

Use **工作資料夾** for `operations.jsonl`, per-analysis `worker.json`,
`analysis.log`, `coverage.json` on incomplete runs, and navigation evidence.
Completed, cancelled and failed working copies are kept for inspection.

For a recoverable navigation error, close the owned native dialog or resolve
the reported cause, then choose **查看錯誤與恢復方式 → 重試**. This retries the
currently selected candidate/observation without importing again. Retry is not
offered when native responsiveness or cleanup is unknown; inspect the native
state first. Existing-session refusal is retained on every attempt.

This package is a local integration candidate, not engineer acceptance.
See `pcie-parity-engineer-trial.md` for unfamiliar-trace and timing validation.
# 2026-10-19 r3 更新

中文／其他 Unicode 路徑的原生選檔匯入改用明確 UTF-8 IPC。請使用
`USB-PCIe-Trace-Triage-UX-20261019-r4.zip`（包含 r3 修復）；r2 保留為歷史比較，已發現
Windows 傳統中文 code page 下的路徑轉碼問題，不建議作為目前試用包。
這項修復不改協定分析、排名或原生定位策略。

## 2026-10-19 r4 更新

修正原生開檔失敗被「清理未確認」覆蓋的訊息。增加舊格式工作副本自動更新；
只在新建副本上呼叫 `OpenFile2`，轉換後重新以唯讀副本擷取。原始檔不覆寫，
來源與顯示副本各自保存 SHA-256，報告與定位使用顯示副本的 Packet 編號。

## 2026-10-20 r7 Flow-first 更新

使用 `USB-PCIe-Trace-Triage-Flow-20261020-r7.zip`，完整解壓後開啟資料夾內
`USBTraceTriage.exe`。Python、pywin32 與本地知識卡均隨包提供，不需要另裝 Python。
LeCroy/PETracer 仍需已安裝；跨機與其他版本需另行驗證。

PCIe 匯入後預設為「流程階段與下一步」。左側最多列出三個待核對區間，詳情顯示
已觀察的階段、仍未確認的初始化證據與下一個核對位置。「定位階段證據」沿用
工具擁有的 PETracer 工作階段；不會改寫原始 Packet 候選的定位位置。
切換為「次要交易觀察」可查看全部原有候選及其原本擷取順序。
「包含較早流程」展開歷史區間，不表示這些區間都是故障。

「工程情境…」是可選輸入。填寫操作及來源；未勾選明確區間時，只作背景，
不能自動將 Link Down 判為預期。勾選時只套用該方向／epoch／Packet 區間；
重新編輯會保留已綁定範圍。清除情境或匯入另一份 trace 不會沿用上一案的設定。
可在較早流程選取含 Link Down 的區間，再輸入該次切換的情境。

工作資料夾包含 `inspection.json`、`flow-analysis.json`、HTML 與 Markdown 報告。
報告、桌面與原生定位取自同一份模型；情境只改變解釋，不改寫原始觀察。
來源清單及知識授權說明位於 `knowledge/pcie/`；目前 Skill 的唯一維護入口為 `.agents/skills/pcie-debug-analysis/`，
供 Codex 研究／審查使用，並未在工具中加入 AI runtime。

單方向 L0 不代表雙向實體 Link、裝置身分或初始化成功。相似 Config Request
不等於 Retry；可見 Completion 狀態不等於完整 Split 對應。未知覆蓋與缺少回覆
不會被當成 Timeout、PCIe PASS 或已確認規格違反。
