# PCIe P4a evidence: hang trace format conversion (2026-09-14)

Status: conversion APPLIED to a disposable writable copy; G1a, G1 full export,
G2a and G3c-0 PASS on the converted copy; triage package generated
(`artifacts/reports/pcie-triage-hang-p4a-20260914/`, run
`20260914T091919Z-4AC65537`, all stages PASS, 1 finding).
Ground truth of this trace: `UNKNOWN` (the engineer suggested using it; it has
not been stated to be a confirmed Fail).

## Authorization and scope

The owner authorized P4a on 2026-09-14 for `Disable ASPM--Insert SD7-hang.pex`
with this boundary: only a disposable writable copy may be converted; the
original `.pex` and the existing read-only copy are not touched. All later
analysis binds to the converted copy.

| File | Role |
| --- | --- |
| `E:\Kent\ASUS NV CRB_20260604\GL9767\Disable ASPM--Insert SD7-hang.pex` | original, never opened by this step |
| `%TEMP%\pcie-hang-20260914-1ec2caab\Disable ASPM--Insert SD7-hang.pex` | earlier read-only copy (prompt cancelled there), never opened by this step |
| `%TEMP%\pcie-p4a-hang-20260914-dcea0027\Disable ASPM--Insert SD7-hang.pex` | disposable writable copy, the only file converted |

## Pre-conversion identity (16:38:26 +08:00)

Disposable copy: 126,339,103 bytes, UTC mtime `2026-06-05T02:25:26.1399833Z`,
attributes `Archive` (writable), SHA-256
`F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6`, equal to
the original.

## Conversion run

- 16:39:47 PETracer 13.26 Build 43 BETA launched; the file name was set in the
  Open dialog and read back identical before Open.
- 16:40:23 the persistent `PCIe Protocol Analysis` dialog was read before any
  click: "File to convert: 'Disable ASPM--Insert SD7-hang.pex'", the text
  stating the file was last modified by LeCroy PETracer 12.36 (Build 19) and
  is about to be updated for 13.26 (Build 43), and the buttons `Update file`
  (id 1), `Update file, backup old version` (id 2934), `Cancel` (id 2).
- 16:40:23.552 `Update file` (id 1) was clicked. The backup variant was not
  used; the untouched original already serves as the backup.
- 16:40:52 PETracer created a cache directory
  `Disable ASPM--Insert SD7-hang.pex.tmp` next to the copy (168 files, about
  69 MB). It is PETracer-owned and was left in place.
- 16:40:53 the copy had grown to 127,664,128 bytes (intermediate state).
- By 16:50 the trace was loaded, status `Ready`, no dialog open.
- 16:51:38 `WM_CLOSE` was sent; PETracer exited at 16:51:56 without a prompt.
- The guarded script itself reported `STOP` at 16:55:24 (exit 3) because its
  load check compared the full path while PETracer shows an ellipsis-shortened
  path (`...\pcie-p4a-hang...0914-dcea0027\...`). This affected only the
  script's completion detection, not the conversion. The helper now accepts a
  shortened title only when its head and tail are a prefix and suffix of the
  exact path.

## Post-conversion identity

PETracer rewrote the copy again while closing (mtime 16:51:48), so the
identity is taken after exit:

| File | Bytes | UTC mtime | SHA-256 |
| --- | --- | --- | --- |
| converted disposable copy | 126,565,918 | `2026-09-14T08:51:48.5449745Z` | `C6E9646BE0624B3EFDD2A31796EDCFC9E3A517C1429491A8101C7E48F96E15AD` |
| original | 126,339,103 | `2026-06-05T02:25:26.1399833Z` | `F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6` |
| earlier read-only copy | 126,339,103 | `2026-06-05T02:25:26.1399833Z` | `F21FCDEB86F8BE1927951C8DE9D169E2DE8AAD404D7336C721A0B21BDDC02CD6` |

Original and read-only copy were re-hashed at 16:51:58 and 16:55:24 with the
same result. Because a close can write to the file, the converted copy was then
set `ReadOnly` so later GUI opens cannot change the analysis target; every
extraction run re-hashes it before and after.

## First reopen of the converted copy (16:56-16:59)

The G1a run opened the read-only converted copy. It reached `Ready` in about
22 s with no format-update prompt, so 13.26 reads the converted file directly.
The run then stopped before any input because the foreground window belonged to
another application (guard by design); no VSE script ran. PETracer was closed
at 16:59:13. Converted copy SHA-256 afterwards: `C6E9646B...` (unchanged);
original and read-only copy unchanged.

## Extraction on the converted copy (17:11-17:18)

Every run opened the read-only converted copy through the guarded GUI helper
(file name read back, description verified before Run, Save Output listing only
that script, PETracer closed). Original, read-only copy and converted copy were
re-hashed before the batch and after every run: always `F21FCDEB...`,
`F21FCDEB...`, `C6E9646B...` with unchanged size and attributes. Logs and
ready/result screenshots are in `artifacts/evidence/pcie-p4a-hang-20260914/`.

| Step | Script | Log SHA-256 | Verifier result |
| --- | --- | --- | --- |
| G1a | `g1a-tlp-count` | `5EEC8CA9...` | `PASS_COUNT_ONLY`: 704 TLP callbacks, first index 3129 (8.277 sec), last index 1484414 |
| capacity gate | none | none | 704 rows at 54 bytes/row, below the verified 10k cap, so `g1b-tlp-rows-10k` serves as the full export; `g1c-tlp-rows-all` was not needed |
| G1 full export | `g1b-tlp-rows-10k` | `9CEE4679...` | `PASS_ROW_EXPORT`: 704 of 704, `trace_end`, `complete_export: true`, rows.json `0E665BB1...` |
| G2a | `g2a-tlp-fields` | `FF34B520...` | `PASS_FIELD_PROBE_OUTPUT`: 704 rows, fields.json `DFC6FC25...` |
| G3c-0 | `g3c0-msg-fields` | `8CFD82F8...` | `PASS_MESSAGE_FIELD_PROBE_OUTPUT`: 3 messages (`PM_PME` @3129, `VENDOR1` @1484399, `SLOTPOWERLIMIT` @1484414), messages.json `F5B4F122...` |

One PETracer process was still listed for a moment after the last run's exit
was observed; it was gone at the next check (17:18:28) without any action.

## Triage package

Input manifest `samples/pcie/triage-input-hang-p4a.json` (with
`trace.provenance`; no GUI association cross-check was run for this trace).
Runner result: 226 non-posted requests, 272 completion candidates (all
`compl_status` 0), association outcomes 224 `COMPLETIONS_OBSERVED`, 1
`SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED`, 1
`NONE_OBSERVED_IN_CAPTURE`. One candidate (`G3B`, `CfgRd0` `Tag 6` from
`000:00.0` at packet 225043, same key again at 225048, 9.512 sec) became F001.
`report.md`, `report.html` and `使用說明.md` each carry the original SHA, the
converted SHA and the packet index caveat before the findings.

Observed but outside the current detectors (reported to the owner, not added to
the report): packet 225048 is the last TLP before a TLP-free stretch; the next
TLPs are the two messages at 10.912 sec (packet indices 1484399 and 1484414).
Vendor packet index is an identifier, not a count, and no causal reading is
made.

## Claims not made

- The conversion is not shown to preserve bytes, packet numbering or decoded
  content. Reports from this trace carry the caveat: packet 編號來自轉換後的
  13.26 trace；尚未證明與原始 12.36 顯示的 packet index 完全一致。 It stays
  until evidence shows the indices agree.
- No compatibility claim is made for the other legacy traces.
- Ground truth stays `UNKNOWN` until the engineer states the trace is a
  confirmed Fail.

## Report provenance support

The runner input manifest accepts an optional `trace.provenance` object
(`original_sha256`, `conversion`, `analysis_target`, `packet_index_note`).
`trace.sha256` is then the converted copy. Validation fails closed when the
keys differ, the original SHA equals the analysed SHA, or the packet index note
is not the exact caveat. G7 and G8 place a `Trace 來源與轉換` block before the
findings, and their contract checks fail when the original SHA, the converted
SHA label or the caveat is missing there. `使用說明.md` repeats the block.
Without `trace.provenance` the 1350 package content is unchanged (re-run
differs only in run id, output paths and the path-bearing findings hash).
