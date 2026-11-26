# PCIe-G9a/G9b/G9c Offline Triage Runner — Evidence (2026-09-14)

Status: **G9a, G9b and G9c PASS (prototype)**. One command turns a verified
extraction bundle into an engineer review package. Engineer review (PCIe-G9)
does not wait for the runner; the runner only removes manual stage chaining.

## Scope (owner decision 2026-09-14)

In scope: G2b → G3a/b → G3c → G3d → G3e → G3f → G7 → G8 from verified extraction
artifacts. Excluded (also recorded in every run manifest): PETracer GUI
automation, COM, opening `.pex` files, running VSE scripts, legacy format
conversion, AI agent, writing skill. GUI extraction stays manual and controlled.

```text
python -X utf8 -B scripts/pcie/run_pcie_triage.py --input-manifest samples/pcie/triage-input-1350.json --output-dir <new directory>
.\run-pcie-triage.ps1 -InputManifest samples\pcie\triage-input-1350.json -OutputDir <new directory>
```

## Input manifest (`pcie.triage-input/v1`)

`trace` (file name, SHA-256, TLP count), `fields` (G2a `fields.json`, SHA-256,
verifier `summary.json`), `messages` (G3c-0 `messages.json`, SHA-256, verifier
`summary.json`), optional `gui_crosschecks`. Example: `samples/pcie/triage-input-1350.json`.

## G9b fail-closed checks

Before any stage runs, the runner stops when:

- an input file is missing or its SHA-256 differs from the input manifest;
- the G2a verifier status is not `PASS_FIELD_PROBE_OUTPUT`, or its canonical hash
  does not describe the given `fields.json`;
- the G3c-0 verifier status is not `PASS_MESSAGE_FIELD_PROBE_OUTPUT`, or its hash
  does not describe the given `messages.json`;
- `messages.json` was verified against a different `fields.json` (other extraction or trace);
- the trace TLP count differs from the G2a verifier rows or the `fields.json` length;
- the output directory already exists (no mixing with old files).

During the run, a non-zero stage exit, a stage exception or a missing expected
output stops the run. A `run-manifest.json` with `status: FAILED` and
`failed_stage` is still written. Tests cover hash mismatch, unverified extraction,
messages from another extraction, TLP count mismatch, existing output directory
and a stage failure (G2b) that stops before any report.

## Run manifest (`pcie.triage-run-manifest/v1`)

Run id, start and finish time, status, input manifest SHA-256, trace identity,
each input path and SHA-256, parameters (G3c 8 TLP rows and 64 packets, G3d 5
rows), Python version, SHA-256 of the runner and every stage script, each stage
status with output hashes, and package hashes.

## 1350 run

Run id `20260914T081330Z-78474DEA`, status `PASS`, stages validate_inputs → g2b → g3ab → g3c → g3d → g3e → g3f → g7 → g8, all PASS.
Package `artifacts/reports/pcie-triage-1350-20260914/`; `run-manifest.json` SHA-256 `6A504B7AB22A169C67D62022B77E0623C818D48C1E492C3F6F2739B64EEC2474`.

| Input | Path | SHA-256 |
| --- | --- | --- |
| fields | `E:/BackUp/Git_EE/lecroy-vse-toolkit/artifacts/evidence/pcie-g2a-20260914/export/fields.json` | `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79` |
| messages | `E:/BackUp/Git_EE/lecroy-vse-toolkit/artifacts/evidence/pcie-g3c0-20260914/export/messages.json` | `08A7307F029E2BB55EC9419EE694ED97EAA1518112AC1C9E288E2AE9D57E1754` |
| gui_crosschecks | `E:/BackUp/Git_EE/lecroy-vse-toolkit/artifacts/evidence/pcie-g2b-20260914/gui-split/crosschecks.json` | `151FEBC497C4311C44C33D5EA3B08504429FDE0B783500C52E2412518C49940A` |
| fields_summary | `E:/BackUp/Git_EE/lecroy-vse-toolkit/artifacts/evidence/pcie-g2a-20260914/export/summary.json` | `8EB8C1EA5291D006B6FEF7F2243492A338E466D5851422C3425758F7420647CC` |

| Package file | SHA-256 |
| --- | --- |
| `report.html` | `B65829E5506FB74192854EEE16DC2D7F5A34BCE8E02C7F9B639A3040819F501D` |
| `report.md` | `F210191DBDB9E96D38CF721313ADA05EBF92CF78165E2D9152021E2521A3027F` |
| `findings.json` | `91B38B2DA1D0608890EE67B664621E79C3D0ADAACDC9CE2C35367DF59EC00E37` |
| `使用說明.md` | `1B5B02199B6DF715AA7D7F7B0CD703D289DA370E8BBD6B0FCF5017E5CFDE3070` |

| Script | SHA-256 |
| --- | --- |
| runner | `AB15643A62C07FDDDAD9DEC1237DEC3BFF664924C572D49DCE0E6552DF196965` |
| g2b | `08279219277E6DB06948C377A3412CF75A42CB0E0FC9EFE56D7711A0E5DEE047` |
| g3ab | `C1B9DDE3C2D6D8107CA6C6A869926FD43ED9479FFF69A8A2D7C89288D0258316` |
| g3c | `60E35CC7ECCFB42875403C07E2EDC684693BFF15F8F7E195D2D719FF901CAF82` |
| g3d | `D9B42CD3B51AE05E5B839EC238E097CABCBBE6F35EED203817458F5F064C2063` |
| g3e | `5573C8A539E83CFA3A465F8E0F8D25AD8FA9860CDD9EE503B9F318E27BC882B8` |
| g3f | `B020ED1C3C769D147A3CD90A889994099B3ACF69AA7030CC87609026AF3B5BBD` |
| g7 | `6FFE6BA41485E5EB9527A154D4D2C9AE72BFB89A997DA080CB79B2EF61C5F31D` |
| g8 | `548F8783F34C25F1901786BB4C4061F6299AA530F080496567790E5F2E1278F4` |

Equivalence with the manual step-by-step outputs: the runner's `findings.json`
findings list is identical to `artifacts/evidence/pcie-g3f-20260914/findings.json`
(only the recorded input paths differ), and the runner's `report.md` differs from
the G7 v2 report in exactly one line, the `findings.json` SHA-256 in 資料來源.

## G9c engineer review package

`report.html` and `report.md` (people), `findings.json` (single source),
`run-manifest.json` (provenance), `使用說明.md` (Traditional Chinese: which file to
open, how to use Go to Packet, limits, and feedback with run id and finding id),
`stages/` (intermediate outputs for tracing one finding). No trace binary, no
screenshots, no agent or skill dependency.

## Limits

- 1350 is an outcome-unknown trace, not a Fail-named trace; PCIe-G9 still needs a
  real Fail trace and engineer feedback.
- The runner trusts the verifier summaries it checks; it does not re-run G1/G2a/G3c-0
  verification or touch the source trace.
