# PCIe runtime evidence — 2026-09-12

P0-B1, B2, B3 and B4: **PASS**, limited to the executable, trace and
unchanged vendor sample identified below. This is a GUI runtime baseline,
not PCIe-P0 qualification or a captured-device PASS judgment.

Historical C1 attempts: **FAIL**, including the channel-only retry that exposed
missing event selection. Neither fixed marker nor DONE made those runs partial
PASS. The subsequent authorized [staircase execution](pcie-staircase-evidence.md)
separately passed C1a-C1d, C2a-C2d and the bounded D1a-D1d projection. It stopped
at that roadmap's D2c BLOCKED on missing triage requirements; E was not started.
The later V1 roadmap adds outcome-unknown D1e; current execution/semantic gate
status is recorded in [PLAN](../PLAN.md). The detailed
failed-run records below remain unchanged as historical evidence.

The B1-B4 round used the owner's sequential-slice instruction. The channel-only
C1 retry had a same-slice stop instruction. The later staircase request replaced
that stop with advancement through individually passed gates, without allowing
a failed/inconclusive prerequisite to be bypassed.

## Identities and input integrity

- Executable: `C:\Program Files\LeCroy\PCIe Protocol Suite\PETracer.exe`.
  ProductVersion `13.26 (Build 43)`; FileVersion `13, 26, 0, 43`; BETA.
  Bytes: 78,978,944. SHA-256:
  `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118`.
  The process used in this session was PID 34952; no prior PETracer process
  was present. This is local application identity, not installer identity.
- Source: `C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`.
  Selected as a **known-source candidate**, not a known-good capture.
- Run root: `C:\Users\reiko\AppData\Local\Temp\pcie-runtime-20260912-30e3b5c6`.
  Two fresh external copies: `b1\S0-Remove SD7-1350.pex` and
  `b4\S0-Remove SD7-1350.pex` below that root. Neither source nor trace binaries
  were placed in Git. Temp copies are disposable, not durable storage.

| Property | Source before/after | Each copy before opening/after closing |
| --- | --- | --- |
| Bytes | 105,224,486, unchanged | 105,224,486, unchanged |
| Last write UTC | `2026-06-11T07:12:55.2721460Z`, unchanged | Same, unchanged |
| Attributes | `Archive`, unchanged | `ReadOnly, Archive`, unchanged |
| SHA-256 | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` | Same, unchanged |

Checks used `Get-Item`, `.VersionInfo`, `Get-FileHash -Algorithm SHA256` and
process/window identity. Source was never opened in PETracer or made read-only;
only copied inputs were opened. No save/convert/annotation operation was used.
The B1 copy was checked after B1 closure and again after B3; both copies and
source were checked after B4 closure.

Vendor root: `C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite\Scripts\VFScripts`.
The installed tree contains one `examp_tlps.pevs` path, under `Examples`.
These hashes were identical before B3 and after B4; nothing was edited:

| Relative file | SHA-256 |
| --- | --- |
| `Examples\examp_tlps.pevs` (4,918 bytes) | `6D87B11DCC12956AFB2618153B677B16D4EB6E27E683D713495279E5005B281C` |
| `VSTools.inc` | `6DCD3760C52F5C5D6C848E15C585D715341D21AAC252E8B4289E19B578C83F7B` |
| `VS_constants.inc` | `799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D` |
| `Examples\examp_tlp_data.inc` | `821A4DCCE6B941E51C4B87BA68DB2F4A2068774366AD039145661C552D3A6C84` |

## Distinct slice observations

Times below are Asia/Taipei (UTC+08:00). Screenshots retain the application,
copy identity and visible result; UI Automation also exposed the full trace
child-window path where the main title was truncated.

| Slice | Observed evidence | Judgment |
| --- | --- | --- |
| B1 | By 12:50:54 the B1 copy displayed packet rows 0–12 and `Ready`; scrollbar navigation displayed 12–24. No incompatible/unsupported/corrupt rejection, crash or hang was observed. Trace was then closed and input integrity checked at 12:51:55. | PASS: actual content loaded and navigable, not just a shell/title. |
| B2 | Reopened B1 copy. `Tools → Run verification scripts` opened `Run verification script(s)` with a script list, `Run scripts` button and output pane. No script had run at this gate. | PASS: observed, repeatable GUI entry. |
| B3 | Selected only `examp_tlps`, whose GUI description matches the installed sample. Run requested at 12:55:08; `Running...` and TLP text appeared. At 12:55:24 result was `DONE`, output ended with `D O N E !!!`, button returned to `Run scripts`. | PASS: unchanged vendor sample executed with observable output and no observed parse/runtime error. |
| B4 | Closed trace and made a new protected B4 copy. Open requested at 12:56:43; by 12:57:04 content was `Ready`, then independently navigated. Repeated the same Tools entry; output was initially empty. Run requested at 12:57:57; observed `Running...`, then `DONE` plus output at 12:58:12. Closed trace and checked source/copies/vendor hashes. | PASS: second B1–B3 sequence reproduced on a fresh copy in the same installed application session. |

Timing is observation-bounded, not a benchmark: second loading was usable by
22 seconds after the open request; vendor runs were DONE by approximately
17 and 15 seconds after their requests. Exact completion instants were not
sampled. First load elapsed time was not reliably recorded because initial
file-dialog input attempts did not submit the intended path.

## Reproduction

1. Verify the executable and source identities above. Make a new external copy,
   set its ReadOnly attribute and verify matching size/hash/mtime. Stop on a
   mismatch. Do not retry against the original or clear ReadOnly to proceed.
2. Launch the named PETracer executable. Choose `File → Open...`, enter the
   complete working-copy path, verify the field, then choose `Open`.
3. Wait for real trace content and `Ready` (an intermediate `Updating
   Navigator...` was observed). Navigate the trace scrollbar and verify changed
   packet rows. A filename, busy dialog or absence of a crash is insufficient.
4. Choose `Tools → Run verification scripts`. Scroll to and select only
   `examp_tlps`; confirm its Transaction Layer packets description. Before
   running, the output area must be empty for this new trace invocation.
5. Choose `Run scripts`. Observe output and a terminal `DONE`, not only
   `Running...`. The unchanged sample calls `ScriptForDisplayOnly()`; its
   success is not a protocol/device conformance result.
6. Choose `Done` in the script view, then `File → Close` for the trace.
   Recheck source/copy hashes, sizes, UTC mtimes and attributes. Retain output
   screenshots bound to the copy path. Repeat with another fresh copy for B4.

## Screenshots

Evidence directory: [runtime screenshots](../artifacts/evidence/pcie-runtime-20260912/).

- [B1 ready](../artifacts/evidence/pcie-runtime-20260912/b1-ready.png),
  [B1 navigation](../artifacts/evidence/pcie-runtime-20260912/b1-navigation.png).
- [B2 Tools menu](../artifacts/evidence/pcie-runtime-20260912/b2-tools-menu.png),
  [B2 entry](../artifacts/evidence/pcie-runtime-20260912/b2-entry.png).
- [B3 selection](../artifacts/evidence/pcie-runtime-20260912/b3-selected.png),
  [B3 running](../artifacts/evidence/pcie-runtime-20260912/b3-run.png),
  [B3 result](../artifacts/evidence/pcie-runtime-20260912/b3-result.png).
- [B4 ready](../artifacts/evidence/pcie-runtime-20260912/b4-ready.png),
  [B4 navigation](../artifacts/evidence/pcie-runtime-20260912/b4-navigation.png),
  [B4 entry](../artifacts/evidence/pcie-runtime-20260912/b4-entry.png),
  [B4 running](../artifacts/evidence/pcie-runtime-20260912/b4-running.png),
  [B4 result](../artifacts/evidence/pcie-runtime-20260912/b4-result.png).

## Findings and claim boundaries

- The trace GUI reports `Errors detected!`. This was not a load rejection.
  Its cause and protocol significance were not investigated; the capture is
  not relabeled known-good or a verified device PASS/FAIL case.
- This path needed no implemented PCIe COM/Automation/host bridge. Whether a
  future programmatic workflow needs COM remains UNKNOWN. Desktop UI control
  is not evidence of a product headless replay API.
- The computer-use skill was read, but its required `node_repl` was unavailable.
  The fallback used a temporary generic Windows GUI helper and screenshots;
  no PCIe application API, COM research or repo host implementation was used.
  Initial filename input attempts were corrected by reading back the exact
  dialog value before the successful open; these were not format rejections.
- Vendor output is runtime evidence only: no own extraction, event-count
  reconciliation, packet correctness analysis or GUI event correlation is
  established by B1–B4. Other captures, other builds and restart reproducibility
  remain untested. The installer/application version relationship is still UNKNOWN.

## C1 — initial fixed-message attempt (FAIL; historical evidence)

After B4 acceptance, a separate [p0-c1-message.pevs](../scripts/pcie/p0-c1-message.pevs)
was created. It declares the same module/input/output types as the vendor
example, uses `VSTools.inc`, calls `ScriptForDisplayOnly()` and emits only
`PCIE_P0_C1_MESSAGE_V1`. It does not read any `in.*` field. Its first-event
callback calls the installed helper's `ScriptDone()` then `Complete()`.
The historical `hello-events.pevs` draft was not changed or executed.

Local GUI discovery deployment added only our script beneath the installed
VSE root in `lecroy-vse-toolkit-poc-20260912-30e3b5c6\p0-c1-message.pevs`.
No installed vendor file was overwritten. Repo and deployed script SHA-256,
identical before and after the run:
`CD8D0406684D244BADF265B27625DA00F5811E2D4F0BAC04BCC7547AB79BDECF`.
This was the initial failed deployment identity. The same deployed path was
subsequently updated for the retry below; the initial failure evidence remains.

A third fresh copy, `c1\S0-Remove SD7-1350.pex` under the same run root,
was checked before opening. It had the same hash, bytes and UTC mtime as the
source, with `ReadOnly, Archive` attributes. It loaded to Ready. On entering
the same Tools path, the GUI discovered `p0-c1-message`; its description
was `PCIe P0-C1 fixed message only - message-v1`, and output was empty.

Run requested at 13:03:05. The GUI then showed `DONE`, but output included:

```text
PCIE_P0_C1_MESSAGE_V1
***ERROR***: No channels found to be sent.
Specify channels for sending in OnStartScript() function.
```

This proves only that the startup hook emitted the fixed marker, not an
error-free script run. **The error overrides the apparent DONE status for
C1 acceptance.** C1 is FAIL; no C2 primitive read or further slice ran.
The unchanged vendor example explicitly calls `SendAllChannels()` in its
startup hook; our script has no channel selection. A minimal channel-setup
correction and retry of the same C1 was the next candidate action, not yet a
confirmed root cause or implemented correction at that initial failure gate.

After `Done → File → Close`, the source and C1 copy retained their hash,
105,224,486 bytes, UTC mtime and original attributes (checked at 13:04:10).
The vendor sample hash was still unchanged. The file-only check found just
the `.pex` file in each copy directory; it did not exclude subdirectories.

Evidence: [C1 loaded input](../artifacts/evidence/pcie-runtime-20260912/c1-ready.png),
[C1 selected/empty output](../artifacts/evidence/pcie-runtime-20260912/c1-selected.png),
[C1 error despite DONE](../artifacts/evidence/pcie-runtime-20260912/c1-result.png).

No COM investigation, PCIe host bridge, JSON event output, completion detector,
count reconciliation, own event extraction, scorer/report integration, USB
implementation change, shared schema, `core/`, governance change, commit or
push occurred. GUI completion observations are not a programmatic completion
implementation. The only product code added is the unaccepted C1 script.

## C1 retry — channel bootstrap only (FAIL)

The owner requested a controlled differential retry, not a new slice. The
only reference inspected for initialization was the already-passed installed
`Examples\examp_tlps.pevs`. It calls `SendAllChannels()` before its TLP-specific
`SendTraceEventOnly(_PKT_TLP)`, `SendTlpType(_ANY_TYPE)` and counter setup.
Only the channel call was transferred; no event selector, counter, packet
parsing or `in.*` access was added. No broader API/documentation search occurred.

The exact source/deployment change, verified against the saved pre-retry bytes:

```diff
     ReportText("PCIE_P0_C1_MESSAGE_V1");
+    SendAllChannels();
 }
```

Repo and deployed script changed from 459 to 482 bytes. Both had the same
post-change SHA-256 before and after retry:
`DFF053B3EB56033115AB1A52B4E536D7BD056CB26864DDB5C9F430C1C8D2E36A`.
The [pre-retry source snapshot](../artifacts/evidence/pcie-runtime-20260912/c1-before-retry.pevs.txt)
preserves the previous 459-byte script and its recorded `CD8D0406...` hash above.
The GUI description, fixed marker and remaining script code were unchanged.

Controlled inputs: same PETracer process (34952), executable/version/hash,
same installed includes, same deployed script path, and the **same** read-only
`c1\S0-Remove SD7-1350.pex` copy used in the failed initial attempt. Before
retry, all these identities matched their recorded values except the intended
one-line script change. B1-B4 were not reopened as milestones or rerun.

The copy reopened to Ready by 13:14:11 (UTC+08:00). The same GUI entry showed
`p0-c1-message` and an empty output pane. Retry was requested at 13:15:58;
the result was visible by 13:15:59:

```text
PCIE_P0_C1_MESSAGE_V1
***ERROR***: No events found to be sent.
Specify events for sending in OnStartScript() function.
```

| C1 acceptance requirement | Retry observation |
| --- | --- |
| Actual own-script execution | VERIFIED: selected C1 produced new output |
| Fixed message observable | VERIFIED: unchanged marker appeared |
| Execution ends normally without errors | FAIL: new runtime error; GUI DONE is insufficient |
| No original channel error | VERIFIED in the visible complete short output |
| No other runtime error | FAIL: `No events found to be sent` |

Root-cause boundary: before retry, missing channel initialization was a
**candidate**. This one-variable comparison confirms that adding channel
selection removes the initial channel diagnostic for this exact execution
setup. It does **not** confirm a complete bootstrap fix or C1 usability. The
new diagnostic reports missing events; the minimum correct event setup remains
unverified. On this new runtime error, testing stopped immediately: no event
configuration was added, no second retry was run, and C2 was not started.

After `Done → File → Close`, checks at 13:17:20 reconfirmed source/copy SHA-256
`1ADB98F8...`, 105,224,486 bytes, UTC mtime `2026-06-11T07:12:55.2721460Z`
and original attributes (`Archive` / `ReadOnly, Archive`). The executable,
vendor sample, `VSTools.inc` and `VS_constants.inc` retained their hashes,
sizes, mtimes and attributes. The failed revised C1 remains deployed at the
same isolated path. A `.pex.tmp` subdirectory was visible in the working-copy
folder before retry; it was not inspected or removed, and trace-byte integrity
claims do not imply that the analyzer creates no auxiliary files/directories.

Evidence: [same loaded input](../artifacts/evidence/pcie-runtime-20260912/c1-retry-loaded.png),
[selected C1 / empty output](../artifacts/evidence/pcie-runtime-20260912/c1-retry-selected.png),
[retry error despite DONE](../artifacts/evidence/pcie-runtime-20260912/c1-retry-result.png).
The computer-use skill's required `node_repl` was still unavailable, so the
existing Windows GUI fallback was reused without adding a host bridge. One
foreground-target mismatch prevented input; fresh observation recovered the
menu before execution. That GUI-tool interruption was not a script failure.

Next candidate action is another explicitly bounded retry of **the same C1**
to establish minimal event-dispatch bootstrap from the passed vendor reference,
without parsing. It was not undertaken in this retry round.
