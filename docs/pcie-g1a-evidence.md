# PCIe-G1a Full-trace Traversal Probe — Evidence (2026-09-14)

Status: **PASS** for count-only traversal of one trace. Not row export (G1b/G1c),
not reproducibility (G1d), not a diagnostic or PASS/FAIL result.

## Inputs

| Item | Identity |
| --- | --- |
| Source trace | `E:\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`, 105224486 bytes, UTC mtime `2026-06-11T07:12:55.2721460Z`, SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Working copy | `C:\Users\reiko\AppData\Local\Temp\pcie-g1a-20260914-25d30c25\S0-Remove SD7-1350.pex`, same size/mtime/SHA-256, ReadOnly |
| Analyzer | `PETracer.exe` 13.26 (Build 43) BETA, SHA-256 `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| Script | `scripts/pcie/g1a-tlp-count.pevs` and deployed copy in `VFScripts\lecroy-vse-toolkit-poc-20260912-30e3b5c6`, both SHA-256 `ECB8EF2B83F25177C1E749250CA19430FEBE11D843A890D025AD7BE94B230094` |

Ground truth for this trace remains UNKNOWN; it was chosen because it is the
already verified loadable trace, not for its outcome.

## Execution (GUI path, no COM)

- 11:07:35 PETracer launched empty. Foreground was repeatedly taken by other
  applications while the owner was using the desktop; every input step was
  guarded and no input reached another application. The owner then paused
  desktop use.
- 11:13:38 File-open dialog path set by `WM_SETTEXT` and read back identical
  before Open; by 11:13:59 the main title showed the exact working-copy path.
  Status bar Ready; packets 0-16 visible ([ready screenshot](../artifacts/evidence/pcie-g1a-20260914/g1a-ready.png)).
  No format-update or other prompt appeared.
- Tools → Run verification scripts opened the script window. The `g1a-tlp-count`
  entry was selected and the description pane read back
  `PCIe G1a full-trace TLP count probe - v1` before Run.
- **11:20:15.255 Run requested; by 11:20:20 the Result column showed DONE**
  and the output pane showed the summary ([result screenshot](../artifacts/evidence/pcie-g1a-20260914/g1a-result.png)).
  Wall-clock runtime is therefore at most about 5 s (observation granularity).
- 11:21:39 Save Output (only `g1a-tlp-count` listed and checked) wrote the vendor log.
  PETracer also updated its own `GenScriptMacros\scripts.ini` at that time.
- 11:22:08 WM_CLOSE to the main window; PETracer exited at 11:22:23 without a
  save prompt. The trace was never saved or converted.

An earlier mis-aimed click (DPI scaling) only selected packet row 12 in the
trace view; no command was triggered by it.

## Output

Retained unmodified as
[g1a-vendor-saved-output.log.txt](../artifacts/evidence/pcie-g1a-20260914/g1a-vendor-saved-output.log.txt),
SHA-256 `C1B551461F30FD5FE863DE8BF0B95DE68F7028A6972DDCA0F1DDE99E14A17A39`
(identical to the external original under `C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite`).

```text
PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none
PCIE_G1A_SUMMARY|tlp_count=938|first_index=1944516|first_time= 4.848 sec|last_index=2121703
------- D O N E !!! -------
```

`python -X utf8 -B scripts/pcie/verify_g1a_log.py artifacts/evidence/pcie-g1a-20260914/g1a-vendor-saved-output.log.txt`
returned `PASS_COUNT_ONLY`: 938 TLP callbacks, first index 1944516 (4.848 sec),
last index 2121703, zero progress markers (938 < 250,000, as expected).

The first TLP index and display time equal the retained D1 evidence for the
same trace. The `OnFinishScript` summary construct worked on this runtime.

## Post-close integrity (checked 11:22:46 +08:00, PETracer not running)

Source trace, working copy (still ReadOnly), PETracer executable, repo script and
deployed script all retained the size, UTC mtime and SHA-256 listed above.

## Limits

- 938 is the number of TLP callbacks delivered to this subscription
  (`SendAllChannels`, `SendTraceEventOnly(_PKT_TLP)`, `SendTlpType(_ANY_TYPE)`).
  It is not a total event count; vendor indices are identifiers.
- The last TLP (index 2121703) was not separately cross-checked in the GUI, and
  no GUI total-TLP count was compared.
- Runtime is bounded by screenshot timing, not measured by the script.
- One trace only; reproducibility is G1d.

## Consequence for G1b

938 TLPs is below both prepared G1b caps (1,000 and 10,000). Those scripts end
only by reaching their cap, so on this trace they would reach normal finish
without their `PCIE_G1B_END` marker and the verifier would reject them. The
capacity gate is trivially satisfied (938 rows at roughly 54 bytes ≈ 50 KB).
G1b is not run until the owner decides how to adapt it.
