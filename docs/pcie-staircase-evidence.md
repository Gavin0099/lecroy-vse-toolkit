# PCIe staircase evidence — 2026-09-12

This is the run record for the owner's earlier C1a-E4 staircase and the later
D1e continuation. The revised V1-testable roadmap in [PLAN](../PLAN.md)
separates outcome-unknown cross-trace capability from semantic PASS/FAIL
qualification at E1a; no existing PASS is reopened. **Current D1e status is
PASS within the first-five TLP projection**, as recorded in the final-closure
section below. Earlier focus interruptions and pending cross-check entries are
historical run states superseded by that closure. E1a remains blocked on
ground-truth provenance and observed test behavior.
Earlier B1–B4 PASS and the two failed C1 attempts remain historical evidence in
[runtime baseline](pcie-runtime-baseline.md); they are not silently rewritten.
Only a passed prerequisite permits advancement. DONE with a runtime error fails.

Terminal result for this historical slice revision: C1a-C1d, C2a-C2d and D1a-D1d PASS within their stated bounds;
D2a/D2b DROP for this run; D2c BLOCKED on missing triage requirements;
E1-E4 NOT STARTED. This is partial completion, not a PCIe-P0/triage PASS.

## Controlled runtime and inputs

Same installed `C:\Program Files\LeCroy\PCIe Protocol Suite\PETracer.exe`,
13.26 Build 43 BETA, PID 34952. Its SHA-256 was rechecked unchanged:
`160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118`.
The GUI path is `Tools → Run verification scripts`, select exactly the named
script, then `Run scripts`. Scripts are deployed to the existing isolated folder
`C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite\Scripts\VFScripts\lecroy-vse-toolkit-poc-20260912-30e3b5c6`.
No vendor file is edited. The computer-use skill was read; `node_repl` remained
unavailable, so the existing temporary Windows GUI helper was reused.

Source: `C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`.
Identity: 105,224,486 bytes; UTC mtime `2026-06-11T07:12:55.2721460Z`;
SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB`.
Source attributes remain `Archive`; copies are `ReadOnly, Archive`.
The source is never passed to PETracer. GUI-created auxiliary directories do
not change the source/trace-byte integrity claim. This is not a known-good
device capture; GUI `Errors detected!` is not interpreted as a device verdict.

Run root: `C:\Users\reiko\AppData\Local\Temp\pcie-staircase-20260912-655482ea`.
C1b/C1c reuse the prior verified copy at
`C:\Users\reiko\AppData\Local\Temp\pcie-runtime-20260912-30e3b5c6\c1\S0-Remove SD7-1350.pex`.
Their post-close hash, size, mtime and attributes matched the pre-run identity.
C1d uses a fresh `c1d\S0-Remove SD7-1350.pex` below the new run root, verified
with the same identity before opening. Capture binaries stay outside Git.

## C1b event bootstrap — PASS

Initialization comparison was limited to installed `examp_tlps.pevs` versus
our script: declarations, callbacks and startup selections. Added only:

```text
SendTraceEventOnly(_PKT_TLP);
SendTlpType(_ANY_TYPE);
```

These subscribe to the vendor-backed TLP event family and any TLP subtype.
They are dispatch bootstrap, not payload/content filtering. No `FilterTlpType`,
packet loop, statistics, data-field access or parsing was transferred. The
runtime helper/callback structure remained unchanged. This is the smallest
vendor-backed candidate used in this run, not a proof that both calls are
individually indispensable or that no alternative subscription is possible.

Before hash: `DFF053B3EB56033115AB1A52B4E536D7BD056CB26864DDB5C9F430C1C8D2E36A`.
After hash (repo and deployed `p0-c1-message.pevs` match):
`6B84B2D8D5F78BB5FC7A182175523FCA6EBC997F910F7DCC5E1D6353BC55A921`.
Exact text comparison verified only those two added calls.

At 13:27:16 Asia/Taipei, the selected C1 script ran from an empty output pane.
By 13:27:17 it showed `PCIE_P0_C1_MESSAGE_V1`, the terminal `D O N E !!!`,
result `DONE` and an enabled `Run scripts` button. The complete short output
contained neither the prior channel/event errors nor a new runtime error.
Progress-bar percentage is not used as completion evidence.

## C1c clean execution — PASS

A separate execution at 13:27:38 used the exact same script and trace.
The fixed message, terminal output and DONE reappeared without runtime errors.
Static inspection confirms that the script reads no `in.*` fields and emits
no trace-derived value: its first callback only calls `ScriptDone()` and
`Complete()`. This establishes clean own-script execution only, not trace
primitive access. C1 execution PASS is limited to this subscription and input;
C1d must separately establish a fresh-copy repeat before C2 work.

## C1d fresh-copy reproducibility — PASS

The new C1d copy loaded to a real trace view by 13:30:59. Reopened VSE showed
empty output; the same unchanged C1 script ran at 13:31:41 and produced the
same fixed marker and normal terminal output by 13:31:42, without runtime
errors. The child-window identity bound the run to the full new copy path
even where the main title was truncated. After closing, source and C1d copy
retained the recorded hashes/size/mtime/attributes; script and vendor includes
also retained their recorded hashes. C1b, C1c and C1d are separate executions.

## C2a observed primitive inventory — PASS

This bounded inventory reuses actual [B4 vendor output](../artifacts/evidence/pcie-runtime-20260912/b4-running.png)
and maps it to the unchanged installed `VSTools.inc` implementations
`ReportEventInfo()` / `ReportTlpEventInfo()`. It is not an exhaustive API list
or proof of availability on all traces. No new extractor was run for inventory.

| Vendor context/helper | Actual vendor output observation | Meaning/limit |
| --- | --- | --- |
| `in.Index` | `TraceEvent:# 2094514` | Vendor trace-event identifier; not a count of selected TLPs |
| `in.Level` | `Level : 0` | Vendor level identifier, no cross-protocol normalization |
| `GetChannelName()` | `Downstream` | Vendor direction label; physical endpoint mapping not established |
| `GetEventName()` | `TLP` | Vendor event-family label |
| `TimeToText(in.Time)` | `5.889 sec` | Display-formatted time only; full timestamp precision not established |
| `in.TLPType`, `in.Type`, `in.Fmt` | `CfgRd0 (0x9 - Type:0x4, Fmt:0x0)` | Observed vendor TLP classification/raw codes |
| `in.LinkWidth`, `GetSpeed()` | `1`, `5.0GT/s` | Vendor reported link metadata; not independent physical measurement |

Next C2b selects only `in.Index` for its first own primitive read. No USB event
names, LTSSM/LFPS meaning or scorer compatibility is inferred from this table.

## C2b/C2c/C2d primitive proof — PASS

The separately deployed [p0-c2-index.pevs](../scripts/pcie/p0-c2-index.pevs)
uses the accepted bootstrap and reads only `in.Index` in its first callback.
Repo/deployment SHA-256:
`3C5E62A106AACE4E20ACDF5FA38B552CBECDE95CACD2553490127977446A9C0E`.
On the C1d copy, C2b at 13:37:13 produced `PCIE_P0_C2_INDEX=1944516` and
normal terminal output. C2c's separate run at 13:37:27 reproduced that value.
No runtime errors appeared in either complete short output.

The dependency probe [p0-c2-index-next.pevs](../scripts/pcie/p0-c2-index-next.pevs)
uses the same subscription, skips just one callback without reading its fields,
then reads `in.Index` from the next callback. No payload parsing was added.
Repo/deployment SHA-256:
`19A06C7E4522838F3F8EBF5E742436AD723EE0AF02E129113B2D122C96DF4BB7`.
C2d at 13:39:47 produced `PCIE_P0_C2_NEXT_INDEX=1944517` and normal terminal
output without a runtime error. The observed value changed with read position;
neither index is embedded as a constant in the probe code. This proves a
bounded trace dependency, not a complete event model or count reconciliation.

## D1a candidate event inventory — PASS for inventory only

| Candidate | Actual support | Potential triage use | Decision/boundary |
| --- | --- | --- | --- |
| TLP | Vendor output plus own two-position index reads; vendor exposes time, direction, type and width | Locate transaction/configuration progress with an exact vendor event reference | Select for one-class bounded extraction; usefulness for diagnosing a device fault remains unproven |
| Direction, link width, TLP subtype | Observed attributes of the above TLP | Context on each selected transaction | Attributes, not manufactured additional event classes |
| Link-state/ordered-set families | Visible GUI content exists but no own primitive extraction evidence yet | Possible future link-transition context | Deferred; not admitted to the extracted set on GUI names alone |
| USB LINK_CMD/LFPS schema | No PCIe equivalence evidence | None established | Not transferred from USB |

This inventory does not fix a final triage model. D1b now tests only a bounded
first-five-TLP projection. Timestamp display text will be preserved as such;
no precise timing, scoring or cross-protocol normalization is authorized by it.

## D1b single-class bounded extractor — PASS

[p0-d1-tlps.pevs](../scripts/pcie/p0-d1-tlps.pevs) emits the first five TLP
callbacks then terminates, using the already accepted bootstrap and installed
vendor helpers. Repo/deployment SHA-256:
`91AAA647D24C4785A2C4418066B0D1A4BABF926E4C09B8F1EA86558EE0C507CA`.
The first execution was observed at 13:46:00 and the separate repeat at
13:46:41. Both complete short outputs contained the same five records and
normal terminal output, without a runtime error. This is bounded repeatability
on one capture, not stable full-trace extraction across traces/versions.

The GUI `Save Output... → selected p0-d1-tlps → Save` also wrote a vendor log
at 13:46:26 beneath `C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite`;
the filename includes the sanitized full working-copy path. The GUI helper
reported a stale dialog-handle inspection error after Save closed the dialog;
re-observation showed the save message and the actual log was located/read.
This helper error is distinct from VSE runtime execution.

## D1c extraction contract — PASS for projection-v1 only

Line grammar: `PCIE_D1_TLP|index|time_text|event|channel|tlp_type|link_width`.
This is a PCIe POC-only, bounded evidence projection, not a canonical normalized
format, final triage model, JSON interface or cross-protocol contract.

| Position | Source/representation | Meaning and limit |
| --- | --- | --- |
| `index` | `in.Index`, unsigned decimal | Vendor trace event reference, not a selected-event ordinal or count |
| `time_text` | `TimeToText(in.Time)`, preserved vendor text | Display-formatted time including its unit; not full precision and not suitable for timing thresholds |
| `event` | `GetEventName()` | Observed `TLP` family |
| `channel` | `GetChannelName()` | Observed `Downstream`; physical endpoint mapping not independently established |
| `tlp_type` | `in.TLPType`, `0x%X` | Raw vendor subtype code, not a USB event mapping |
| `link_width` | `in.LinkWidth`, decimal | Vendor-reported lane count |

Marker `PCIE_D1_TLP_SPIKE_V1 cap=5 time=vendor_display_text` identifies this
projection. The script stops after five callbacks, so absence from this output
does not imply absence from the trace. Traces containing fewer than five TLPs
and zero-TLP inputs have not been qualified. Whole-trace coverage, event count
reconciliation, precision timing and fault interpretation are not claimed.
The containing evidence binds every row to the exact trace/executable/script
hashes; a detached row alone is not sufficient evidence identity.

## D1d GUI/vendor cross-check — PASS within the bounded projection

After closing VSE, `Search → Go to Packet...` was used to navigate to vendor
index `1944516` on the same C1d copy. The GUI displayed all five extracted TLP
references, with intervening DLLP packets correctly absent from our TLP-only
projection. The five displayed TLPs have width `x1`; the first is `Msg / MsgD`
and the next four are `Cfg / CfgRd0`. The unchanged vendor `VSTools.inc`
`GetTlpTypeName()` maps the corresponding vendor symbols to `MsgD` and
`CfgRd0`; `VS_constants.inc` documents their numeric IDs as 14 and 9. This is
vendor-representation evidence, not a redefinition of PCIe packet-header codes.

| Vendor index | Own raw subtype | GUI classification | GUI timestamp, seconds | Own vendor display time |
| --- | --- | --- | --- | --- |
| 1944516 | `0xE` | Msg / MsgD | `4.847933004000` | ` 4.848 sec` |
| 1944517 | `0x9` | Cfg / CfgRd0 | `4.847933068000` | ` 4.848 sec` |
| 1944519 | `0x9` | Cfg / CfgRd0 | `4.847937356000` | ` 4.848 sec` |
| 1944521 | `0x9` | Cfg / CfgRd0 | `4.847939414000` | ` 4.848 sec` |
| 1944523 | `0x9` | Cfg / CfgRd0 | `4.847948900000` | ` 4.848 sec` |

The coarse time strings are consistent with the GUI values; equal strings
must not be interpreted as simultaneous events. Native timestamp precision,
timestamp reference conventions and physical Downstream endpoint mapping are
not independently established by this comparison. No whole-trace count or
fault diagnosis follows. The Go-to dialog input was verified through its
UI value before navigation; unreliable IME keystrokes were not accepted as
evidence that the requested packet had been reached.

## D2 decision and terminal blocker

D2a and D2b are **DROP for this run**, not PASS for another extractor. TLP
attributes do not create new classes. Link-state, ordered-set or DLLP families
may be future candidates, but their necessity for a concrete triage question
has not been established. No additional class was implemented simply to fill
the roadmap or mirror USB. DROP does not assert unavailability or uselessness.

D2c is **BLOCKED**. D1's bounded projection-v1 is fixed and checkable, but it
cannot honestly be frozen as the final set of events/fields necessary for PCIe
triage without a target scenario and acceptance evidence. The sample provenance
document explicitly contains no independently justified PASS/FAIL pair. A
narrow read-only non-trace-file listing of the selected `ASUS NV CRB_20260604`
source subtree returned no companion files. Capture names are not test verdicts,
and the GUI's `Errors detected!` is not a classifier label. No other source tree
was searched or trace opened to work around this requirement gap.

Needed to resume D2c: a concrete PCIe question (what behavior/failure is being
triaged) and expected behavior/acceptance criteria, so the necessary event set
can be evaluated. A trustworthy PASS/FAIL pair and supporting test observations
are a separate future E3 input, not an added prerequisite for D2c. This is
missing task information, not a request to reapprove each slice.
E1-E4 remain **NOT STARTED** behind D2c: no scorer, adapter, report, JSON output,
host bridge, automation/COM research or common abstraction was added. The
overall request is partially complete; PCIe-P0 and PCIe triage are not PASS.

## Retained evidence and final integrity

Evidence directory: `artifacts/evidence/pcie-staircase-20260912/`.
Screenshots are observations, not a substitute for the identities and scope
above. C1c's separate run is recorded in the execution observations; its
redundant screenshot with an unrelated window overlay is not retained here.

| Evidence | Purpose |
| --- | --- |
| [c1b-before.pevs.txt](../artifacts/evidence/pcie-staircase-20260912/c1b-before.pevs.txt) | Exact channel-only failing revision for the two-line bootstrap differential |
| [c1b-selected.png](../artifacts/evidence/pcie-staircase-20260912/c1b-selected.png), [c1b-result.png](../artifacts/evidence/pcie-staircase-20260912/c1b-result.png) | Selected own script and clean event-bootstrap result |
| [c1d-ready2.png](../artifacts/evidence/pcie-staircase-20260912/c1d-ready2.png), [c1d-entry.png](../artifacts/evidence/pcie-staircase-20260912/c1d-entry.png), [c1d-result.png](../artifacts/evidence/pcie-staircase-20260912/c1d-result.png) | Fresh-copy content, empty VSE entry, clean repeat |
| [c2b-selected.png](../artifacts/evidence/pcie-staircase-20260912/c2b-selected.png), [c2b-result.png](../artifacts/evidence/pcie-staircase-20260912/c2b-result.png), [c2c-result.png](../artifacts/evidence/pcie-staircase-20260912/c2c-result.png), [c2d-result.png](../artifacts/evidence/pcie-staircase-20260912/c2d-result.png) | Primitive read, separate same-value repeat and changed-position result |
| [d1-selected.png](../artifacts/evidence/pcie-staircase-20260912/d1-selected.png), [d1-result.png](../artifacts/evidence/pcie-staircase-20260912/d1-result.png), [d1-repeat-result.png](../artifacts/evidence/pcie-staircase-20260912/d1-repeat-result.png) | One-class first-five spike and separate identical repeat |
| [d1-vendor-saved-output.log.txt](../artifacts/evidence/pcie-staircase-20260912/d1-vendor-saved-output.log.txt) | Unmodified vendor Save Output log; SHA-256 `31EF4279896C216F4FA6928D275D5D3388F7FAC576A059CF4CBC5926D992EEF3` |
| [d1-gui-crosscheck.png](../artifacts/evidence/pcie-staircase-20260912/d1-gui-crosscheck.png) | Actual same-trace packet view of the five projected TLPs |
| [final-closed.png](../artifacts/evidence/pcie-staircase-20260912/final-closed.png) | Trace closed before final integrity verification; application left open |

After final trace closure (observed at 13:52:07 Asia/Taipei), source and both copies used in this round retained
the recorded 105,224,486-byte size, SHA-256 and UTC mtime. Source attributes
remained Archive; both copies remained ReadOnly, Archive. The executable and
all four vendor files listed in the runtime baseline retained their hashes.
All four own scripts matched their corresponding deployments and recorded
hashes. No vendor file or source trace was edited; only external working-copy
auxiliary data, our isolated script deployments and the GUI output log were
created/used outside the repo. The original `.pex` was never loaded or saved.

This is a controlled bug-fix/extraction-spike proof, not general qualification.
Negative runtime behavior is evidenced by the retained earlier channel/event
failures; the corrected C1 passes without reading trace fields. No zero-TLP,
shorter-than-cap, malformed-trace or other-version runtime behavior was tested.
No such missing test is silently counted as a PASS.

Final read-only checks: `Get-Item` / `Get-FileHash` for the stated identities;
exact C1 backout comparison against the retained pre-event-bootstrap snapshot;
no `in.*` reads or packet-report helper in C1; five saved D1 rows checked against
the reviewed GUI/vendor values and a clean terminal log; nine changed product
text files passed whitespace checks and 56 local Markdown links resolved;
`git diff --check` passed. `tools/pcie` and `core` remained absent. All 16
retained evidence files hash-match their originals. These static/log checks
supplement the actual GUI executions; they do not simulate VSE or broaden the
runtime qualification. Existing unrelated working-tree changes were preserved.

## D1e first attempt — historical inputs READY, runtime NOT RUN

The latest owner decision separates technical cross-trace capability from
semantic qualification. D1e needs a distinct trace with observable extraction
and GUI sample cross-check, not PASS/FAIL outcome labels. Those labels belong
to E1a. The former D1e pair blocker is superseded, not a technical failure.

Trace A is the accepted `S0-Remove SD7-1350.pex`; its existing first-five TLP
execution/cross-check above is retained. Trace B is
`C:\Users\reiko\Desktop\Kent\ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1335.pex`.
Selection was by convenient size, not filename semantics. Both outcome labels
are UNKNOWN. Distinct paths/hashes do not prove independent test conditions.

| Input | Bytes | UTC mtime | SHA-256 | Attributes |
| --- | --- | --- | --- | --- |
| Source A | 105224486 | `2026-06-11T07:12:55.2721460Z` | `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` | Archive |
| Source B | 107086178 | `2026-06-11T07:13:41.4022556Z` | `9C90FB3351B5D9260D6A966463A9A7DEE21595B5094A45AF391E7ED598482E81` | Archive |
| B working copy | 107086178 | same as Source B | same as Source B | ReadOnly, Archive |

Prepared working copy:
`C:\Users\reiko\AppData\Local\Temp\pcie-d1e-20260912-72f33a5b\b\S0-Remove SD7-1335.pex`.
The existing repo/deployed `p0-d1-tlps.pevs` both retained SHA-256
`91AAA647D24C4785A2C4418066B0D1A4BABF926E4C09B8F1EA86558EE0C507CA`.
No extraction code or deployment changed. PETracer PID 34952 remained the same
13.26 Build 43 BETA executable/hash above; the vendor sample and two includes
also matched their earlier identities. Both sources, copy and executable
matched the precheck exactly after the attempted GUI activation. This is
preparation integrity, not post-extraction proof.

The computer-use skill and its guidance/confirmation rules were read. Its
`node_repl` runtime was absent from the tool list, so the unchanged prior
temporary Windows GUI helper was used as fallback. The initial screen capture
was occluded by another app and was deleted, not retained as evidence. No
input was sent to that app. Refreshing the PETracer window and attempting
restore/activation returned `SetForegroundWindow=False`; the target did not
receive foreground. UIA focus recovery reported `Target element cannot receive
focus`. A subsequent read-only check still showed `ForegroundIsTarget=false`.
Following the skill's recovery boundary, GUI input stopped and manual
foreground activation was requested. Only the PETracer window was restored;
its title remained the empty application shell, with no loaded trace.

D1e is **NOT RUN**, not PASS and not an extractor/trace FAIL. There is no Trace B
output or GUI cross-check yet. Resume by observing the existing PETracer window
in foreground, rechecking the prepared identities, then opening only the B
working copy and running the unchanged script. Do not reopen A's accepted
milestone or add extraction logic to address a window-focus issue. After D1e,
STOP at E1a; optional signal additions are DROP/SKIP and final triage model
freeze is DEFER until a diagnostic use case. E1a still needs only the two
trace identities and their normal/abnormal observed behavior, not root cause.

## D1e resumed run — extraction executed, cross-check pending

This continuation uses the same Trace A/B identities, protected B copy and
unchanged deployed script listed above. Foreground activation succeeded at
14:23:11 on 2026-09-12 (Asia/Taipei); executable, both sources, B copy and
repo/deployed extractor hashes were reverified before opening the B copy.
No extraction logic, subscription, output format or deployment was changed.
The prior focus blocker was not a permanent trace/runtime conclusion.

The B working-copy path was verified through the file dialog value before
Open. At 14:26:26 the GUI showed a loading operation, not yet acceptance.
By 14:27:57 it showed the exact B path, Ready and actual packet rows 0-12.
`Errors detected!` remained uninterpreted capture status, not a test verdict
or format rejection. Both source outcomes remain UNKNOWN.

Via `Tools → Run verification scripts`, the empty output pane and selected
`p0-d1-tlps` description were observed. Run requested at 14:28:46; by
14:28:47 the output showed the fixed projection marker, five records,
`D O N E !!!`, DONE and an enabled Run scripts button. GUI Save Output wrote
the complete log at 14:29:33. Full log inspection found no runtime error:

```text
PCIE_D1_TLP_SPIKE_V1 cap=5 time=vendor_display_text
PCIE_D1_TLP|2000010| 4.401 sec|TLP|Downstream|0xE|1
PCIE_D1_TLP|2000011| 4.401 sec|TLP|Downstream|0x9|1
PCIE_D1_TLP|2000013| 4.401 sec|TLP|Downstream|0x9|1
PCIE_D1_TLP|2000015| 4.401 sec|TLP|Downstream|0x9|1
PCIE_D1_TLP|2000017| 4.401 sec|TLP|Downstream|0x9|1
------- D O N E !!! -------
```

These are raw vendor values on B, not a PASS/FAIL divergence analysis. The
time remains rounded vendor display text. No full-trace coverage, interval
precision or diagnostic interpretation is implied by five records.

After leaving VSE, `Search → Go to Packet...` opened the dialog for B.
Its index edit was focused and observed as PID 34952 / AutomationId 1004.
Before the separate value-entry action, focus changed to another process;
the guard raised `Unexpected focus; no input` before setting any value.
Window re-enumeration still found B and its Go-to dialog, but the one recovery
attempt returned `Activated=false`, `ForegroundIsTarget=false`. GUI input
stopped under the computer-use recovery rule and the owner's stop-on-error
instruction. No keys, text or clicks were sent to the unrelated app.

Thus the new output is real extraction evidence, but GUI cross-check is
**PENDING**. The Go-to dialog still has no verified requested index and the
trace remains open. Both sources and B copy retained the stated hashes,
sizes, UTC mtimes and attributes at the ensuing read-only check; the exe,
extractor/deployment and vendor include hashes were also unchanged. This
check while loaded is not the required post-close integrity proof.

Retained evidence under `artifacts/evidence/pcie-d1e-20260912/`:

- [b-ready.png](../artifacts/evidence/pcie-d1e-20260912/b-ready.png): exact B input and real trace content.
- [b-vse-list.png](../artifacts/evidence/pcie-d1e-20260912/b-vse-list.png): unchanged extractor selected, empty output.
- [b-extraction-result.png](../artifacts/evidence/pcie-d1e-20260912/b-extraction-result.png): five TLP rows and normal terminal result.
- [b-save-result.png](../artifacts/evidence/pcie-d1e-20260912/b-save-result.png): vendor output-save confirmation.
- [b-vendor-output.log.txt](../artifacts/evidence/pcie-d1e-20260912/b-vendor-output.log.txt): unmodified complete vendor log, SHA-256 `EEF7BC8BA228CF389EBC5710E72FC58267CBA033994F33AF60677CFC8A8EFC75`.
- [b-goto-dialog.png](../artifacts/evidence/pcie-d1e-20260912/b-goto-dialog.png): attempted cross-check entry only, NOT a matched packet view.

All six evidence files hash-match their originals. Two temporary images with
unrelated window overlays were excluded/deleted rather than used as evidence.
The external original log resides beneath
`C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite`, named
`p0-d1-tlps - [C_Users_reiko_AppData_Local_Temp_pcie-d1e-20260912-72f33a5b_b_S0-Remove SD7-1335.pex].log`.

D1e overall remains **BLOCKED_BY_GUI_FOCUS / CROSS_CHECK_PENDING**, not PASS
and not a cross-trace extraction FAIL. Resume needs the Go-to dialog in
foreground without other-window interaction, then index 2000010, GUI sampling,
trace closure and both-source/copy integrity checks. Reuse the captured output;
no new script, rerun of A or further implementation is needed for this step.
E1a still lacks a qualified pair; E1b and later slices have not started.

## D1e final closure — 2026-09-12

This continuation supersedes the pending status above, not the historical
observations. The existing B extraction log was reused, not rerun. The
computer-use skill was read; node_repl was unavailable and only the existing
foreground-guarded PowerShell helper was used. Fresh enumeration found PID
34952, main window 51776758 and Go to Packet 16846240 for the exact protected
B copy. Foreground was initially false; normal activation then returned true.
After a fresh focused-edit observation (PID 34952 / AutomationId 1004 /
ValuePattern), the requested index was set and read back as 2000010.

The resulting actual GUI showed all five expected TLP packets unobscured:

| Packet | GUI family / subtype | GUI timestamp (seconds) | Link width |
| --- | --- | --- | --- |
| 2000010 | Msg / MsgD | 4.400691948000 | x1 |
| 2000011 | Cfg / CfgRd0 | 4.400692004000 | x1 |
| 2000013 | Cfg / CfgRd0 | 4.400694042000 | x1 |
| 2000015 | Cfg / CfgRd0 | 4.400697370000 | x1 |
| 2000017 | Cfg / CfgRd0 | 4.400699404000 | x1 |

Indices, families (vendor type 0xE then four 0x9), x1 and rounded 4.401 sec
agree with the retained five-row B log. GUI timestamps above are human-read
GUI evidence only; the extractor still emits coarse display text, not these
precise timestamps. Downstream remains a raw vendor label, not a newly
qualified physical-direction mapping. No packet semantics or symptom analysis
was performed.

New screen captures contained an unrelated application thumbnail below the
five checked rows. They were excluded from durable evidence and the handoff;
no new clean B cross-check screenshot is claimed. The values above record
direct visual observation in this session. Existing clean B execution/input
screenshots and the original output log remain linked above. The old Go-to
dialog screenshot is not promoted to cross-check proof.

File → Close was executed without saving the trace. After closure the main
window title contained only the application identity; refreshed UIA showed
Ready and no loaded Trace View child. Subsequent SHA-256 checks (before
14:55:02 +08:00) matched:

- Source A: `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB`.
- Source B and B working copy: `9C90FB3351B5D9260D6A966463A9A7DEE21595B5094A45AF391E7ED598482E81`.
- Repo and deployed extractor: `91AAA647D24C4785A2C4418066B0D1A4BABF926E4C09B8F1EA86558EE0C507CA`.

B copy remained 107086178 bytes, UTC mtime 2026-06-11T07:13:41.4022556Z,
ReadOnly / Archive. All eight source hashes were independently rechecked for
P1 and matched the earlier inventory; metadata remained stable during hashing.
No original capture or script was edited. No new executable/version
qualification is claimed in this closure.

D1e = PASS for the same first-five TLP projection on two distinct files,
with GUI sampling and post-close integrity. Not full-trace coverage, diagnostic
usefulness, statistical independence, or PASS/FAIL ground truth. P1/P2/P3 are
documented in [engineer handoff](pcie-engineer-handoff.md); E1a remains blocked
on actual test background. P4 and downstream diagnostic work were not run.

## Optional P4 compatibility sweep — blocked during initial load attempts

After D1e/P1-P3, six remaining source traces were copied into a separate
external read-only workspace and checked against their source SHA-256 before
any open attempt. For the first candidate,
`Disable ASPM--Insert SD7-hang-2.pex`, PETracer displayed a format-update
prompt stating that the trace had last been modified by LeCroy PETracer 12.36
(Build 19) and would be updated for current 13.26 (Build 43). The prompt warns
the changed file might not be readable by older software. See the retained
[prompt screenshot](../artifacts/evidence/pcie-p4-20260912/legacy-format-update-prompt.png).

The update was canceled; no VSE script was run on this input. Its read-only
working-copy SHA-256 remained
`7147529BC0DAAD709085874DEEC64C5D5E8F28CE9F6CC5BBC52BADAF0E287479`, matching
the source. No conversion was applied. A second open attempt on
`Disable ASPM--Insert SD7-hang.pex` reached a modal dialog, but its contents
were not successfully observed before it was canceled; therefore its cause is
UNKNOWN. No script ran on either trace. The other four copies were not opened.
P4 is **DEFERRED / LEGACY_FORMAT_COMPATIBILITY** by the owner's decision; it
does not block E1a. It is not an extractor FAIL, and no native compatibility
claim is made for these traces or the untried ones. Ground truth remains
UNKNOWN for all six. Reopen only if E1a identifies one of these legacy inputs
as necessary; then handle format conversion in a separate P4a using a
disposable copy, source protection and explicit pre/post hashes. Conversion
does not prove bit-equivalence.
