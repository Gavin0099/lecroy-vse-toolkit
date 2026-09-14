# PCIe sample inputs

2026-09-12 runtime update: `S0-Remove SD7-1350.pex` was rehashed and opened
only through fresh external read-only copies in PETracer.exe 13.26 Build 43 BETA.
B1-B4 passed for this exact input and the unchanged vendor `examp_tlps.pevs`;
source/copy integrity remained unchanged. See [runtime evidence](../../docs/pcie-runtime-baseline.md).
It entered B1 as a **known-source candidate**, not a known-good trace. Successful
loading does not establish capture health; the GUI displayed `Errors detected!`.
At that B1-B4 checkpoint the other seven candidates were untested. Current extraction/outcome status is in the [engineer handoff](../../docs/pcie-engineer-handoff.md); all eight source hashes were reverified on 2026-09-12.

Later [staircase evidence](../../docs/pcie-staircase-evidence.md) records clean
own-script runs, primitive reads and five TLP records checked against the GUI
on another protected copy of the same source. It does not validate capture
health or a PASS/FAIL label. That roadmap stopped at its D2c model-freeze gate;
the [revised V1 roadmap](../../PLAN.md) now separates outcome-unknown D1e
cross-trace capability from E1a ground truth. `S0-Remove SD7-1335.pex` is Trace B:
a different verified source was opened through its protected copy and the
unchanged extractor produced five TLPs with no logged runtime error. Focus was
lost before GUI sampling in that attempt. A later continuation completed five-record GUI sampling and post-close integrity, closing D1e as PASS within that bounded projection.
No PCIe comparison pair was qualified. D1e does not require PASS/FAIL labels.

## Single-trace inspection preview

The first presentation sample uses Trace A (`S0-Remove SD7-1350.pex`) and the
retained D1 VSE output plus GUI cross-check. The [2026-09-12 Markdown baseline](../../artifacts/reports/pcie-inspection-1350-20260912/report.md)
and [HTML baseline](../../artifacts/reports/pcie-inspection-1350-20260912/report.html)
remain unchanged in commit `5806d18`. After owner feedback that the first
version was hard to understand, a [plain-language Markdown revision](../../artifacts/reports/pcie-inspection-1350-20260913/report.md)
and [HTML revision](../../artifacts/reports/pcie-inspection-1350-20260913/report.html)
were generated from the same observations. See the [observation contract](../../docs/pcie-inspection-observation-contract.md).

The revision explains the bounded read and unknown test outcome before showing
technical identities. It does not change the data: only the first five emitted
TLP rows are shown, ground truth is UNKNOWN, diagnostic result is NOT EVALUATED,
and the trace binary remains external. F0e UX review is still open.

## Offline triage runner (PCIe-G9a)

After the manual, controlled GUI extraction has produced verified G2a fields and
G3c-0 messages, one command builds the engineer review package:

```powershell
.\run-pcie-triage.ps1 -InputManifest samples\pcie\triage-input-1350.json -OutputDir artifacts\reports\<new-run-directory>
```

The input manifest names the trace identity and TLP count, the verified
`fields.json` and `messages.json` with their SHA-256 and verifier summaries, and
optional GUI cross-checks. The runner stops if any hash, verifier status, TLP
count or extraction binding does not match, and never opens a trace, drives
PETracer, uses COM or runs VSE. The output folder contains `report.html`,
`report.md`, `findings.json`, `run-manifest.json` and `使用說明.md`. See
[runner evidence](../../docs/pcie-g9-runner-evidence.md).

## Bounded two-trace HTML comparison

`scripts/pcie/build_inspection_comparison.py` creates an offline HTML view from
two existing F0 `observations.json` files. It requires both inputs to use the
same PETracer executable and extractor, contain five TLP rows, and record GUI
cross-checks. The page, titled `PCIe Trace Inspection Comparison` (F0f-1,
2026-09-14), lists what each trace's own five-row sample contains under
**Observed**, lists what is **Not established** (which trace is normal or
abnormal, whether differences indicate a fault, whether five rows represent the
full trace, whether same-position rows are corresponding events, root cause),
and shows sample composition counts with an adjacent note that they are not
full-trace statistics. Outcome-like filename tokens such as `Fail` or `hang`
appear only when present, as filename hints. It does not align timestamps,
compute A-B differences, or claim that similarly numbered rows are the same
event.

Example (replace the input paths with two generated observation bundles):

```powershell
python -B scripts/pcie/build_inspection_comparison.py `
  --trace-a "path\to\trace-a\observations.json" `
  --trace-b "path\to\trace-b\observations.json" `
  --output "artifacts\reports\pcie-comparison\comparison.html"
```

The command reads the JSON inputs only; it does not run VSE or open `.pex`
files. Its output is descriptive, keeps ground truth UNKNOWN and diagnostic
result NOT EVALUATED, does not re-verify the underlying `.pex` or evidence
files, and refuses to overwrite an existing HTML file. The
requested 1329/1335 HTML has not been generated: 1329 has no extraction
evidence, and neither trace currently has a saved F0 observation bundle. 1335
has no retained clean GUI cross-check image, so its bundle cannot be built
under the unchanged v1 contract until that evidence is recovered (F0g). As of
2026-09-14 this comparison is a side branch, not the PCIe mainline; see PLAN.

P0-A status on 2026-09-11: eight owner-designated external `.pex` candidates
were located and fingerprinted. During the live baseline check, the
`PCIeProtocolSuite-offline-repo-25.28.43-BETA.exe` installer was still running
and the target installation directory was empty. Decoder compatibility, actual
event contents and GUI correlation remain unverified. No synthetic output or
USB capture substitutes for PCIe extraction evidence.

## Owner-designated source

2026-09-14 relocation: the eight captures now reside in
`E:\Kent\ASUS NV CRB_20260604\GL9767`. Size, UTC mtime and SHA-256 of all
eight were re-verified identical to the inventory below; the former
`C:\Users\reiko\Desktop\Kent\...` path no longer exists. Historical evidence
and committed manifests keep the path that was valid when they were produced;
new manifests must use the E: path.

The supplied path was resolved by listing the immediate parent directories to:

```text
C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767
```

The originally supplied `ASUS NV CRB\_20260604\GL9767 trace` spelling does not
exist on this machine. The resolved directory contains the eight files below
and no subdirectories. The owner authorized reference inspection; redistribution
rights, capture author, analyzer model and acquisition configuration are unknown.
Names such as `hang` and `Fail` are source labels, not verified outcomes. Original
filename spelling is preserved. No PASS/FAIL pair is selected for P0.

## Source identity inventory

Read-only directory enumeration and `Get-FileHash -Algorithm SHA256` were used
again for this P0-A baseline. Size and UTC mtime remained identical during the
inspection for all eight files, and the values match the inventory below. This
establishes an identity baseline and metadata stability during inspection, not
before/after PCIe execution integrity. No working copies were created and no
capture was opened by an analyzer.

| File | Bytes | Last write UTC |
| --- | ---: | --- |
| Disable ASPM--Insert SD7-hang-2.pex | 113113593 | 2026-06-05T02:24:20.7864439Z |
| Disable ASPM--Insert SD7-hang.pex | 126339103 | 2026-06-05T02:25:26.1399833Z |
| G3-Power on wwth SD7-1329.pex | 406998300 | 2026-06-05T02:26:41.7865905Z |
| G3-Power on wwthouut SD7-1328.pex | 121698585 | 2026-06-05T02:26:37.1593724Z |
| S0-Insert SD7-1334.pex | 354152683 | 2026-06-12T03:57:09.6956271Z |
| S0-Remove SD7-1329-Fail.pex | 150552514 | 2026-06-11T08:41:12.2089248Z |
| S0-Remove SD7-1335.pex | 107086178 | 2026-06-11T07:13:41.4022556Z |
| S0-Remove SD7-1350.pex | 105224486 | 2026-06-11T07:12:55.2721460Z |

| File | SHA-256 |
| --- | --- |
| Disable ASPM--Insert SD7-hang-2.pex | `7147529BC0DAAD709085874DEEC64C5D5E8F28CE9F6CC5BBC52BADAF0E287479` |
| Disable ASPM--Insert SD7-hang.pex | `F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6` |
| G3-Power on wwth SD7-1329.pex | `66DAB50A6100FED0739445C8C7BB54E80E7D4D3D042D54D4064FD3BD9AEF77E0` |
| G3-Power on wwthouut SD7-1328.pex | `3A9DB43C017AD6269E2EB77D5060F3DC7818DD6B29B744217727175952D0C504` |
| S0-Insert SD7-1334.pex | `86F2CCF6BCFFC51A1CCADCB4C8D49EF7EE6C3E92DEE8D329CCB2008027EE665C` |
| S0-Remove SD7-1329-Fail.pex | `D704C0052D0D3635FD95F041A86A67ACB6598E6B1371EF23180E6EDBA3BA25D5` |
| S0-Remove SD7-1335.pex | `9C90FB3351B5D9260D6A966463A9A7DEE21595B5094A45AF391E7ED598482E81` |
| S0-Remove SD7-1350.pex | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |

## Handling and later acceptance

Keep capture binaries outside Git. This directory holds provenance and replay
instructions only; vendor scripts/includes are referenced from the installed
software rather than copied here. The repository's existing USB ignore rules
must not be assumed to exclude PCIe capture extensions.

Before accepting a sample, record:

- external source path or redacted identifier;
- origin (capture owner or exact vendor sample reference) and handling rights;
- actual trace format/extension and compatible analysis software;
- capture device and configuration when known; mark unknown values explicitly;
- source size, SHA-256 and UTC mtime;
- separate working-copy path and before/after integrity evidence;
- selected software executable/version and subsequent script revision.

No redistribution permission is implied by local access or vendor origin.
Follow the [P0-A setup baseline](../../docs/setup/pcie-protocol-suite.md).
Use the revised [PCIe slices in PLAN](../../PLAN.md): B1 opens one protected
trace copy, B2 locates the GUI VSE entry, B3 runs an unchanged vendor sample,
and B4 reproduces those observations. These are separate slices; this sample
inventory does not authorize their execution or programmatic replay.
