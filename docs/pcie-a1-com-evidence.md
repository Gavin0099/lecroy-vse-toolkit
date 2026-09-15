# PCIe-A1 evidence: COM automation qualification (2026-09-14)

Status: **A1_PASS** (run2). COM stays outside the formal flow; the verified GUI
route remains the fallback. Ground truth of 1350 stays `UNKNOWN`.

## Question and scope

Can COM, with no mouse/keyboard input to the PETracer GUI, run the existing
`g1a-tlp-count` VSE script on the known-good trace 1350 and reach the same
semantic result as the verified GUI route?

Owner decision: COM unfrozen for this probe only. Not done in A1: hang or other
traces, legacy conversion, `HideAppWindow`, batch runs, `ExportToJsonFile`,
LTSSM/DLLP, G2/G3 scripts over COM, runner changes. Log byte identity was not
a PASS condition; the semantic result was.

## Inputs

| Item | Identity |
| --- | --- |
| source (hashed only, never opened) | `E:\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`, 105,224,486 bytes, SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| working copy (read-only, new for A1) | `%TEMP%\pcie-a1-com-20260914-d8880bac\S0-Remove SD7-1350.pex`, same size and SHA-256 |
| VSE script | deployed `g1a-tlp-count.pevs`, SHA-256 `ECB8EF2B83F25177C1E749250CA19430FEBE11D843A890D025AD7BE94B230094`, equal to `scripts/pcie/g1a-tlp-count.pevs` |
| GUI baseline | `artifacts/evidence/pcie-g1a-20260914/g1a-vendor-saved-output.log.txt`, re-verified `PASS_COUNT_ONLY`: 938, first 1944516 (4.848 sec), last 2121703 |
| API source | installed `PEAutomation.tlb` (signatures read with `pythoncom.LoadTypeLib`, no server start) and `Documents\PCIeAutomationManual.pdf` (`RunVerificationScript`, `GetVScriptEngine`, `LaunchVScript`, `_IVScriptEngineEvents`, `ITrace::Close`) |

## Route

`scripts/pcie/a1_com_g1a_probe.py` (pywin32):

1. refuse to start if PETracer is already running; hash source, copy, script
2. `win32com.client.Dispatch("CATC.PETracer")` (starts `PETracer.exe` as COM local server)
3. `OpenFile(working copy)`
4. `GetVScriptEngine(full .pevs path)`, event sink attached, `Tag = 0xA1`
5. `LaunchVScript()` (asynchronous); pump messages until `OnVScriptFinished`,
   collecting every `OnVScriptReportUpdated(newLine)`
6. `trace.Close()` (IPETrace default policy `WAIT_FOR_CLOSE`), release objects,
   wait for the PETracer process to exit; re-hash source and copy

No window was hidden, and no keyboard or mouse input was sent. The window was
allowed to appear.

## Runs

| Run | Result | Notes |
| --- | --- | --- |
| attempt 0 | not started | probe crashed before any COM call: `tasklist` output (cp950) decoded as UTF-8. No output directory, no PETracer process. Fixed by decoding with `mbcs`. |
| run1 (17:43) | `A1_PARTIAL` | every control step succeeded and the captured text contained the correct summary, but the probe joined events with no separator, so header and summary merged into one line and the parser found neither. Probe defect, not a COM defect. Kept as `artifacts/evidence/pcie-a1-com-20260914/run1/`. |
| run2 (17:44) | `A1_PASS` | events joined with line breaks (each event is one `ReportText` call). |

run2 detail:

- `CATC.PETracer` created (6.0 s, one PETracer process)
- `OpenFile` returned after 6.7 s
- engine created; `VScriptName` = the full deployed script path
- `LaunchVScript` returned; `OnVScriptFinished` arrived about 0.9 s later with
  result `2` (`DONE`) and tag 161 (`0xA1`)
- 9 report events; text SHA-256 `6218B99E16F3C4B5AFFA72F30F417B531187ADC21AF9DEDAC822ABC7C40D9EFE`
- `Close` succeeded; no PETracer process remained afterwards
- source and working copy: size and SHA-256 unchanged

## Semantic comparison with the GUI route

| Field | GUI route | COM run2 |
| --- | --- | --- |
| header `PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none` | 1 | 1 |
| `tlp_count` | 938 | 938 |
| `first_index` / `first_time` | 1944516 / 4.848 sec | 1944516 / 4.848 sec |
| `last_index` | 2121703 | 2121703 |
| runtime-error marker | none | none |
| `verify_g1a_log.check_log` | accepted | accepted (informational) |

Text difference against the GUI saved log (CR removed): the banner names the
full `.pevs` path instead of `folder\script`, and the GUI's Save Output footer
(`Output was saved on ...`) and trailing blank lines are absent. Everything
between is identical.

## Claims not made

- Hidden/background execution, other traces, legacy-format prompts under COM,
  multi-trace batches, and G1b/G2a/G3c-0 over COM are untested.
- Timing numbers are single observations, not benchmarks.
- A1 does not change the runner, the GUI extraction procedure or any report.
