# PCIe-P0-A setup baseline

Status: `PASS` for P0-A setup baseline, as of 2026-09-12.
The installed executable identity and VSE locations are now verified by read-only
filesystem inspection. This accepts the owner's narrowed installed-runtime
inventory gate. At that gate, application launch, trace compatibility and VSE
execution were UNKNOWN. P0-A PASS does not mean PCIe-P0 PASS.

Subsequent runtime work: [B1-B4 evidence](../pcie-runtime-baseline.md) records
PASS for one exact candidate trace, the GUI VSE entry and two unchanged vendor
sample runs. The historical C1 channel-only retry remained FAIL on an event
selection error. Later [staircase evidence](../pcie-staircase-evidence.md) records
clean C1 execution/reproduction, trace primitive reads and a five-TLP projection
cross-checked with the GUI. That round stopped at its D2c on missing triage
requirements. The later V1 roadmap adds D1e and its current gate status is recorded
in [PLAN](../../PLAN.md); E has not started. These results do not broaden P0-A.

Observed identity note: the installer/package displayed `25.28.43-BETA`
(September 11), while the installed `PETracer.exe` reports `13.26 (Build 43)`
and product identity BETA (September 12). The relationship between these
identifiers is UNKNOWN; no equivalence, numbering conversion, or packaging
error is inferred. Preserve both observations when investigating any later
compatibility issue. This difference does not invalidate the P0-A inventory PASS.

Still unproven: execution of the historical repo draft, full-trace extraction,
other trace compatibility and PCIe triage correctness. The later own-script
results are bounded to their documented scripts, subscription and input.
Whether a future programmatic path requires COM remains UNKNOWN.

## Installed inventory — 2026-09-12

| Item | VERIFIED local observation |
| --- | --- |
| Executable | `C:\Program Files\LeCroy\PCIe Protocol Suite\PETracer.exe` |
| Product identity | `Teledyne LeCroy PCIe Protocol Analysis - BETA` |
| Product version | `13.26 (Build 43)` |
| File version | `13, 26, 0, 43` |
| Executable bytes / SHA-256 | 78,978,944 / `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| Installed VSE root | `C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite\Scripts\VFScripts` |
| Files under VSE root | `VSTools.inc` (31,256 bytes), `VS_constants.inc` (10,096), `VSTemplate.pev_` (13,700), `Examples\examp_tlps.pevs` (4,918) |

Evidence: PowerShell `Get-ChildItem -Recurse -File` restricted to the two LeCroy
PCIe installation roots and the five named files; executable `.VersionInfo`;
`Get-FileHash -Algorithm SHA256` on the installed executable. Inspection date:
2026-09-12, approximately 12:29 Asia/Taipei. No application was launched.

The executable and installed VSE references suffice for this inventory. No
additional bundled component was demonstrated necessary by P0-A. Its GUI
entry evidence was document-backed only at that time. Sample provenance and integrity
policy below are retained from September 11; captures were not rehashed or
opened in this inventory-only follow-up.

This document is deliberately limited to the PCIe setup baseline. It does not
establish PCIe event extraction, a canonical event schema, programmatic replay,
completion detection, GUI correlation, or a host bridge.

## Owner decisions and scope boundary

- PCIe and USB remain in this repository for now, but their implementations are
  isolated.
- PCIe is an independent POC. No `core/`, common abstraction, or shared
  USB/PCIe schema is established.
- `pcie event record` is only a possible future minimum POC evidence shape; it
  is not a canonical normalized format.
- The P0-A round ends with the inventory PASS. Current slice definitions are in
  [PLAN](../../PLAN.md). Subsequent B/C work uses the owner's separate runtime
  continuation instruction; this setup baseline itself grants no runtime work
  or `tools/pcie/` bridge authority.

## Historical version references — observed 2026-09-11

These historical official/package observations are retained, not rechecked on
September 12. The actual installed version is recorded separately above.

| Lane | Evidence | What it means |
| --- | --- | --- |
| Official currently listed beta | Teledyne LeCroy's PCI Express analysis-software page lists package `2026.12`, containing PCIe Analysis Software `13.38` and LinkExpert `5.38`, released 2026-08-18. | Official availability only; not proof of anything installed locally. |
| Official currently listed non-beta line | The same page lists package `2026.10`, containing PCIe Analysis Software `13.36` and LinkExpert `5.36`, released 2026-07-22. | Official availability only; not the local installation identity. |
| Local package observed | `C:\Users\reiko\Desktop\Kent\PCIeProtocolSuite-offline-repo-25.28.43-BETA.exe`; file version `13.26.43.0`, product version `13.26`, product `PCIe Protocol Suite Setup`, company `Teledyne LeCroy`, SHA-256 `04525ACD07387E9B39F4ECE3FDB23164456CEFE12CB3FE41F98F5927EE0455A1`, Authenticode `Valid`. | Installer identity only. It is not the installed application version. |
| Local package payload observed | Temp archive `13.26PCIe Protocol Suite.zip`, 86,006,267 bytes, SHA-256 `3D7DCD50D7160F563E4B1E8A2FCE8B590A8169D86A0B1C4BFAD2D18D44F75505`, with 7,555 ZIP entries. | Package-content evidence only; it is not proof that installation completed. |

Official references:

- [PCI Express analysis software downloads](https://www.teledynelecroy.com/support/softwaredownload/psgdocuments.aspx?standardid=3)
- [PCIe VSE Reference Manual](https://cdn.teledynelecroy.com/files/manuals/petracer_vse_manual.pdf)

The official page also says that bundled downloads contain multiple
components. P0-A does not infer that LinkExpert, analyzer drivers, hardware
support packages, or any other bundled component is required for this POC.
Their necessity remains UNKNOWN until the selected trace and actual runtime
entry point require them.

## Historical pre-install observations — 2026-09-11, superseded above

Checks were read-only. No PCIe application, trace, COM object, or script was
launched.

| Item | Current observation | Evidence status |
| --- | --- | --- |
| PCIe Suite installation target | `C:\Program Files\LeCroy\PCIe Protocol Suite` exists, but has zero children while the installer is running. | VERIFIED observation; installation incomplete/unknown |
| Installer process | `PCIeProtocolSuite-offline-repo-25.28.43-BETA.exe` is running from the Desktop installer path with a responsive window titled `PCIe Protocol Suite 25.28.43-BETA Setup`. | VERIFIED observation |
| PCIe Suite package payload | The temp payload archive contains `PCIe Protocol Suite/Scripts/VFScripts/VSTools.inc`, `VS_constants.inc`, `VSTemplate.pev_`, and PCIe `.pevs` examples. | VERIFIED at package level; not installed-runtime evidence |
| Installed executable and actual installed build | No executable is present in the target directory. No installed PCIe/LinkExpert entry was returned by the checked machine and user uninstall registry views. | UNKNOWN |
| Installed VSE files | Expected local path `C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite\Scripts\VFScripts` does not exist. The same files are present only inside the temp installer payload. | UNKNOWN for installed location; package support VERIFIED |
| Script invocation entry | The official manual documents `Tools > Run verification scripts`, selection, and `Run scripts` from the PCIe Protocol Suite GUI. | DOCUMENT-VERIFIED; local runtime unverified |
| CLI/headless or COM invocation | No local executable or invocation path was confirmed, and no COM/Automation probe was run. | UNKNOWN |
| PCIe trace candidates | Eight owner-designated `.pex` files exist under the external GL9767 directory and were fingerprinted; no capture was opened. | VERIFIED as source candidates; compatibility UNKNOWN |

The installer process being present, and even a complete-looking payload
archive, is not installation proof. The target directory must be rechecked
after installation exits before the installed executable and VSE locations can
be recorded.

## VSE and trace prerequisites

The official VSE manual provides documentation-level evidence that:

- PCIe VSE is a utility in PCIe Protocol Suite for processing recorded PE
  traffic.
- A main verification script uses the `.pevs` extension and is expected under
  `..\Scripts\VFScripts` of the PCIe Protocol Suite folder.
- Scripts include the vendor `VSTools.inc` file.
- The documented GUI entry is `Tools > Run verification scripts`; the selected
  script is then run from the VSE dialog.
- The manual uses `.pex` as a PE trace example and mentions `.pem` for a
  multi-segment trace. This documents examples, not compatibility of the
  local capture set with the not-yet-installed runtime.

The installer payload independently contains the expected `VSTools.inc`,
`VS_constants.inc`, `VSTemplate.pev_`, and example `.pevs` files. Its local
installer script also names `PETracer.exe` as a target executable and contains
post-install COM registration operations. These are package-script facts only;
they do not prove that the files were installed, that COM is needed for P0-A,
or that any host bridge should be created.

The September 11 setup answer was (installed identity/location superseded above):

- Known script entry: GUI `Tools > Run verification scripts`.
- Known script file convention: `.pevs` plus vendor include files.
- Local VSE location: UNKNOWN; package contents are present, but the documented
  installed location is not present.
- Local executable and version: UNKNOWN; only the 13.26 installer and payload
  identity are verified, not the installed executable.
- Local `.pex` trace support: UNKNOWN until the installed application opens a
  disposable working copy successfully.

A pre-existing untracked `scripts/pcie/hello-events.pevs` file was observed in
the working tree. It was not executed, modified, or used as P0-A evidence.

## External sample provenance

The owner-designated source directory is:

```text
C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767
```

The supplied directory contains eight `.pex` candidates. Their filenames,
byte sizes, UTC mtimes, and SHA-256 values are recorded in
[`samples/pcie/README.md`](../../samples/pcie/README.md). A read-only
recheck of those identities matched the recorded inventory. This establishes
source identity at inspection time; it does not establish analyzer decoding,
trace compatibility, or a PASS/FAIL meaning for names containing `Fail` or
`hang`.

The captures remain outside Git. No redistribution permission is inferred from
local access. Capture owner, analyzer model, acquisition settings, and handling
rights remain UNKNOWN unless separately supplied.

## Source and working-copy integrity policy

When runtime verification becomes possible:

1. Keep the source capture outside Git and record its external path or redacted
   identity, size, SHA-256, and UTC mtime before analysis.
2. Create a separate disposable working copy in a fresh external output
   directory. Do not pass the original source to the analyzer.
3. Start with the working copy read-only and record its attributes, size,
   SHA-256, and UTC mtime before and after execution.
4. Verify both source and working-copy identity after the run. If read-only
   execution is rejected or either identity changes, record the failure and
   stop; do not silently fall back to the original or to a writable input.

No PCIe working copy was created and no PCIe runtime integrity result exists in
this P0-A round. The existing USB controlled read-only result is not PCIe
evidence.

## P0-A gate result — inventory-time snapshot

| Required P0-A item | Result |
| --- | --- |
| Suite/software identity recorded | DONE: installed PCIe Protocol Analysis BETA identity verified. |
| Local version and executable confirmed | DONE: installed PETracer.exe, 13.26 Build 43; file identity recorded above. |
| VSE availability/location/invocation recorded | DONE for baseline: installed files/location verified; known GUI entry documented. Actual script execution remains UNKNOWN. |
| Trace prerequisite and sample provenance recorded | Yes for candidate provenance; trace compatibility remains UNKNOWN. |
| Source/working-copy integrity rule recorded | Yes as policy; no PCIe execution evidence exists. |
| VERIFIED and UNKNOWN separated | Yes. |

P0-A is `PASS` within the owner's installed-inventory scope. The prior installer
blocker is closed. The earlier text treating a successful trace-open as a P0-A
exit requirement is superseded by the owner's narrower follow-up instruction.
Trace compatibility, GUI behavior, script execution, programmatic replay and
event acquisition remain UNKNOWN; none was tested here.
No P0-B or later work is started by this document.
