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
retained D1 VSE output plus GUI cross-check. See the generated
[Markdown report](../../artifacts/reports/pcie-inspection-1350-20260912/report.md),
[HTML report](../../artifacts/reports/pcie-inspection-1350-20260912/report.html),
and [observation contract](../../docs/pcie-inspection-observation-contract.md).
The sample says extraction PASS only for the first five emitted TLP rows;
ground truth is UNKNOWN and diagnostic result is NOT EVALUATED. It does not
include the trace binary or assess the entire capture.

P0-A status on 2026-09-11: eight owner-designated external `.pex` candidates
were located and fingerprinted. During the live baseline check, the
`PCIeProtocolSuite-offline-repo-25.28.43-BETA.exe` installer was still running
and the target installation directory was empty. Decoder compatibility, actual
event contents and GUI correlation remain unverified. No synthetic output or
USB capture substitutes for PCIe extraction evidence.

## Owner-designated source

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
