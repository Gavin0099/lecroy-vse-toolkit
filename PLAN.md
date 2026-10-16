# Plan

## Objective

Verify that LeCroy USB Protocol Suite VSE can read a large USB trace, expose useful decoded events, and deliver machine-readable data to a host that can support bounded diagnostic triage.

The repository name remains `lecroy-vse-toolkit` because that is the existing checkout and remote identity. The working posture is experimental/lab; no product or analyzer claim is implied.

## PCIe feasibility scope (revised 2026-09-12)

The owner adopted same-repository USB/PCIe work with isolated implementations.
Existing USB results retain their original scope. No common core is established.
P0-A setup baseline is accepted. The owner's latest instruction authorizes
sequential execution: verify each slice separately, then proceed on PASS
without repeated confirmation. FAIL/BLOCKED or a required scope decision stops
the sequence; this does not combine B1, B2 and B3 into one acceptance claim.
The owner's subsequent staircase instruction replaces the C1-only retry stop:
close each evidence gate in order, proceed on PASS without reconfirmation,
and stop on FAIL/BLOCKED or a required owner decision. No speculative later
implementation, presumed three-class event set or automatic C5 reuse follows.
The latest diagnosis-first V1 roadmap supersedes prior D2/E ordering and IDs:
D1e → E1a ground truth → E1b diagnostic question → D2c/D2d/(D2e)/D2f
signal sufficiency and model freeze → E2a-E2d minimal triage → E3a-E3e testing
→ F1 structured findings → F2 Markdown / F3 HTML → F4 UX alignment
→ F5 Engineer Review Build.
B1-B4 and C1a-D1d are not reopened. Each slice is validated before advancement;
E3 is the final integrated test series, not permission to postpone all checks.
From D1e through the E3e analysis gate there are 14 required slices and two conditional slices: D2e adds only
one signal if evidence proves TLP insufficient; E3d may defer if no second
ground-truth pair is available. Unknown ground truth is not a technical D1e
prerequisite, but it cannot be guessed to bypass E1a.
Analysis V1 is established only at E3e; the engineer-evaluable MD/HTML first
release additionally requires F1-F5. These are distinct delivery gates.
The earlier E4a report/UX proposal is replaced by F1-F5, not a parallel task.
Broader multi-trace coverage and automation/host work remain outside this
review-build path; no COM/host implementation follows without observed need.
The prior USB independent-pair validation remains a
separate pending task, not a PCIe prerequisite or a reopened USB milestone.

| Slice | Scope | State |
| --- | --- | --- |
| PCIe-P0-A | Setup baseline and external sample provenance | PASS for setup inventory (2026-09-12): installed PETracer.exe 13.26 Build 43 BETA and VSE files/location verified; September 11 sample provenance and integrity policy retained. Trace compatibility and script execution remain UNKNOWN. PCIe-P0 is not PASS. |
| PCIe-P0-B1 | Trace Open Baseline | PASS (2026-09-12): exact candidate copy loaded, Ready and navigable packet content; post-close integrity unchanged. |
| PCIe-P0-B2 | VSE Entry Discovery | PASS: actual Tools → Run verification scripts dialog/list observed before any script run. |
| PCIe-P0-B3 | Vendor Sample Execution | PASS: unchanged examp_tlps.pevs produced output and DONE on the selected trace. |
| PCIe-P0-B4 | Minimal Execution Evidence | PASS: B1-B3 reproduced on a fresh protected copy; identities and GUI evidence retained. |
| PCIe-P0-C1a | Channel Bootstrap | PASS for the narrow channel diagnostic: SendAllChannels removed it; historical overall C1 attempt remained FAIL with no events. |
| PCIe-P0-C1b | Event Bootstrap | PASS: vendor-backed TLP subscription removed event error; fixed marker, DONE, no new runtime error. |
| PCIe-P0-C1c | Clean Minimal Execution | PASS: separate fixed-message run, normal end and zero observed runtime errors; no trace-field reads. |
| PCIe-P0-C1d | Reproducibility | PASS: fresh read-only copy and reopened VSE reproduce clean execution; post-close integrity unchanged. C1 own-script execution PASS, not extraction. |
| PCIe-P0-C2a | Primitive Inventory | PASS: actual prior vendor output mapped to installed helpers; bounded inventory in staircase evidence, no extractor. |
| PCIe-P0-C2b | One Primitive Read | PASS: own script read vendor in.Index=1944516. |
| PCIe-P0-C2c | Primitive Reproducibility | PASS: separate same-trace execution returned 1944516 again. |
| PCIe-P0-C2d | Trace Dependency Proof | PASS: skipping the first callback changed the read to 1944517; no runtime error. |
| PCIe-P0-D1a | Candidate Event Inventory | PASS for bounded candidate inventory: TLP with observed metadata; triage usefulness remains a hypothesis, no scorer. |
| PCIe-P0-D1b | Single Event Extractor | PASS for bounded spike: first five TLP records reproduced in two runs; no full-trace coverage claim. |
| PCIe-P0-D1c | Extraction Contract | PASS for D1 projection-v1 only: field/unit/identity and cap documented in staircase evidence; not the final triage model or shared schema. |
| PCIe-P0-D1d | Cross-check | PASS for five-record projection: exact GUI packet references/families/widths and coarse time agree; vendor subtype references documented. No full-trace or physical-channel claim. |
| PCIe-P0-D1e | Cross-trace Extraction | PASS (2026-09-12): existing B output matched five actual GUI TLPs; trace closed and A/B source plus B copy hashes unchanged. Same extractor on two distinct files; first-five projection only, no ground-truth or full-coverage claim. |
| PCIe-P0-E1a | Ground-truth Pair Qualification | BLOCKED on ground truth: trustworthy PASS/FAIL provenance, test operation and observed behavior. Does not block technical D1e. Since 2026-09-14 a non-blocking reference track for the PCIe-G single-Fail mainline. |
| PCIe-P0-E1b | Diagnostic Question Freeze | NOT STARTED; fix one operation → normal expectation → FAIL symptom → question for triage, after E1a. |
| PCIe-P0-D2c | Candidate Signal Model | NOT STARTED; derive candidate PCIe signals from the qualified diagnostic question, not API availability. No scorer design. |
| PCIe-P0-D2d | TLP Sufficiency Test | NOT STARTED; test whether existing TLP extraction supplies observable evidence relevant to that question on the qualified pair. Current cap/display time do not establish full counts or precise timing. |
| PCIe-P0-D2e | Additional Signal Spike | CONDITIONAL / NOT STARTED; add only one justified signal if D2d establishes a gap; DROP if TLP is sufficient. Historical extra-class DROP does not prejudge this new test. |
| PCIe-P0-D2f | V1 Event Model Freeze | NOT STARTED; after E1a/E1b and sufficiency evidence, fix signals, PCIe-only schema and necessary/excluded fields. No triage implementation before freeze. |
| PCIe-P0-E2a | Raw PASS/FAIL Divergence | NOT STARTED; reproducible count/timing/sequence differences within validated extraction coverage and units, without scores or heuristics. |
| PCIe-P0-E2b | First Meaningful Divergence | NOT STARTED; at least one difference relevant to the failure symptom and explainable from GUI/trace, not metric proliferation. |
| PCIe-P0-E2c | Normalized Evidence Contract | NOT STARTED; minimal PCIe triage-consumable evidence contract, not USB/PCIe canonical schema or report UX. No assumed USB scorer reuse. |
| PCIe-P0-E2d | Minimal Triage Runner | NOT STARTED; one defined extraction → comparison flow on the two traces, no AI ranking or assumed host requirement. |
| PCIe-P0-E3a | First End-to-end PASS/FAIL Test | NOT STARTED; real qualified pair through the whole pipeline; different scores alone are insufficient. |
| PCIe-P0-E3b | Explanation Cross-check | NOT STARTED; findings trace back to GUI/packet/timestamp evidence, not black-box scores. |
| PCIe-P0-E3c | Repeatability | NOT STARTED; same pair reproduces findings/anchors/evidence; no all-trace or cross-version claim. |
| PCIe-P0-E3d | Second-pair Sanity Check | CONDITIONAL / NOT STARTED; second known pair checks overfit, DEFER permitted if unavailable. |
| PCIe-P0-E3e | PCIe V1 Testable Gate | NOT STARTED; at least one real qualified pair produces stable, credible, traceable analysis. Not a production/full-coverage claim. |
| PCIe-P0-F1 | Finding Contract | NOT STARTED; after E3e, establish PCIe analysis structured findings as the authoritative report input (analysis.json or equivalent). This is not a USB/PCIe canonical extraction schema. |
| PCIe-P0-F2 | Markdown Report | NOT STARTED; automatically render inputs, symptom, candidates, evidence and limitations from F1 findings in engineer-readable language. No independent analysis in the renderer. |
| PCIe-P0-F3 | HTML Report | NOT STARTED; render the same F1 findings as HTML, preserving findings/evidence/limitations shared with Markdown. No trace reanalysis or different verdicts. |
| PCIe-P0-F4 | USB / PCIe UX Alignment | NOT STARTED; align report structure, cards, PASS/FAIL comparison and evidence navigation only. Do not share or equate diagnostic semantics, event classes or scorers. |
| PCIe-P0-F5 | Engineer Review Build | NOT STARTED; one qualified real case plus structured findings, generated MD/HTML and evidence traceable back to LeCroy. This prepares the first engineer evaluation; it does not establish positive feedback or measured time savings. |

Prior D2 optional-class DROP/SKIP decisions remain historical: no extra class
was implemented, and old statuses do not complete newly defined slices.
Model freeze is now D2f and explicitly follows E1a/E1b. E1a establishes labels
and observations, E1b fixes one use case, and only then can D2 determine signal
necessity. The candidate TLP projection is not the final diagnostic model.

This revision replaces the earlier B=event/GUI correlation, C=programmatic
execution, D=completion/counts/JSON, and E=qualification-only roadmap. Old
references to those letters are historical, not current execution instructions.
The former F abstraction candidate remains deferred outside this sequence;
the new F1-F5 reporting slices do not revive shared-core architecture work.

### Engineer-review delivery boundary

E2c defines the minimum PCIe analysis evidence consumed by the triage flow.
F1 subsequently fixes the structured finding output consumed by both report
renderers. "Canonical" at F1 means the authoritative PCIe report input only;
it does not formalize a shared USB/PCIe event schema. Exact fields are decided
at their gated slices, not implemented by this roadmap update.

F5's intended local delivery is one qualified PASS/FAIL case with
`analysis.json` (or equivalent structured findings), `report.md`, `report.html`
and enough input/packet/time/context identity to return to the original LeCroy
evidence. MD and HTML must reflect the same analysis result. The existing
source-preserving trace policy remains: captures stay outside Git, referenced
by verified identities or supplied as appropriately authorized separate copies.
Do not relabel the current unknown-outcome A/B captures as PASS/FAIL to create
this package. No report or review build exists merely because these filenames
are specified here.

Engineer review should assess whether the suggested regions are worth looking
at, whether they actually reduce manual search effort, and which missing PCIe
evidence would improve usefulness. Those benefits require review evidence;
F5 readiness does not itself prove them. Better signals, heuristics, ranking
and candidate root-cause inference belong to a later V2 decision after useful
engineer feedback, not this V1 implementation path.

Evidence and missing inputs: [PCIe setup](docs/setup/pcie-protocol-suite.md),
[runtime evidence](docs/pcie-runtime-baseline.md),
[staircase evidence](docs/pcie-staircase-evidence.md) and
[sample policy](samples/pcie/README.md). P0-A PASS is limited to installed
inventory. The historical hello-events.pevs draft remains unexecuted and is not
runtime evidence or the C1 implementation. No host or formal event schema is
adopted. Installer/package `25.28.43-BETA` and installed executable
`13.26 (Build 43)` BETA remain separate observed identities; their relationship
is UNKNOWN.

Current work: D1e complete; P1 manifest, P2 status matrix and P3 engineer handoff prepared in [handoff](docs/pcie-engineer-handoff.md). P4 is DEFERRED / LEGACY_FORMAT_COMPATIBILITY and does not block E1a: one trace showed a verified v12.36 format-update prompt, a second open reached a modal with unrecorded cause (identified 2026-09-14 as the same v12.36 Build 19 format-update prompt for `Disable ASPM--Insert SD7-hang.pex`; cancelled, no conversion, source and copy identities unchanged; P4a conversion then owner-authorized and applied the same day to a disposable writable copy only, converted SHA-256 `C6E9646B...`, original and read-only copy unchanged; see [P4a evidence](docs/pcie-p4a-hang-evidence.md)), and four traces remain untried; no extractor ran on these attempts. Reopen a separate P4a only if E1a confirms a required PASS/FAIL trace is among the legacy-format inputs. The earlier stop at E1a applies only to the PASS/FAIL reference track; the 2026-09-14 owner decision moved the V1 mainline to single-Fail triage (PCIe-G below). C1a-C1d, C2a-C2d and D1a-D1d retain
their documented bounded PASS. Trace A is `S0-Remove SD7-1350.pex`; Trace B
is the distinct `S0-Remove SD7-1335.pex`, selected by convenient size from the
existing owner-authorized Kent inventory. Both outcome labels remain UNKNOWN.
Different path and hash establish distinct files, not statistical independence
or known capture/test conditions. No filename is promoted to ground truth.

### Single-Fail triage mainline (PCIe-G, owner decision 2026-09-14)

The V1 mainline is single-Fail-trace triage: one Fail `.pex` is narrowed to a
few ranked candidate locations, each with its reason, evidence packets, a
navigable LeCroy window and its limitations. A PASS trace becomes an accuracy
and ranking reference, not a required V1 input. First-version output is
candidates only: no automatic root cause, device responsibility, or claim that
a candidate explains the user-visible failure.

This supersedes the D1e -> E1a -> ... -> F5 ordering as the V1 path. E1a, E1b,
D2c-D2f, E2a-E2d and E3a-E3e remain a non-blocking PASS/FAIL reference track;
their states are unchanged and none becomes PASS through this decision. For the
single-Fail path, F1-F5 are replaced by PCIe-G5/G7/G8/G9. The F0 inspection
branch, including the comparison renderer, is retained as a side branch. The
`PCIe-G` prefix is distinct from the governance `G0` decisions in this plan.

| Slice | Scope | State |
| --- | --- | --- |
| PCIe-G1a | Full-trace Traversal Probe | PASS (2026-09-14, 1350 protected copy; evidence in `docs/pcie-g1a-evidence.md`): 938 TLP callbacks, first index 1944516 (4.848 sec), last index 2121703; normal finish with summary, zero runtime-error text, zero progress markers (count below 250,000); Run 11:20:15 to DONE visible by 11:20:20 (about 5 s or less); post-close source/copy/executable/script identities unchanged; log SHA-256 `C1B551461F30FD5FE863DE8BF0B95DE68F7028A6972DDCA0F1DDE99E14A17A39`. Original scope: count TLP callbacks from start to normal finish with no per-row output. PASS: exactly one header, DONE, finish summary, zero runtime-error text, consistent progress markers, total TLP callback count and GUI-observed wall-clock time recorded. Verified GUI path only; 1350 protected copy first. The vendor index is not an event count. Script `scripts/pcie/g1a-tlp-count.pevs` SHA-256 `ECB8EF2B83F25177C1E749250CA19430FEBE11D843A890D025AD7BE94B230094`, identical copy in the existing isolated `lecroy-vse-toolkit-poc-20260912-30e3b5c6` VFScripts folder; `scripts/pcie/verify_g1a_log.py` checks the saved log. |
| PCIe-G1b | Bounded Row Export Probe | PASS (2026-09-14, evidence `docs/pcie-g1b-g1d-evidence.md`): GUI sample matched row 469 (packet 2097003, Cfg/CfgRd0, 5.897 sec, x1) and row 938 (packet 2121703, Cpl/CplD, 6.055 sec, x1); row 1 matched earlier D1 GUI evidence. 1k v2 on the 1350 copy: `trace_end`, one END, 938 rows, TSV and canonical JSON re-read equal, first five rows equal D1, DONE 1.2 s after Run, 51891-byte log. Design (v2, owner decision 2026-09-14): rows until cap or natural trace end, whichever comes first; exactly one `PCIE_G1B_END|rows=N|reason=cap|trace_end` guarded by an EndSent flag across the `ScriptDone` and `OnFinishScript` paths. Six D1-verified fields only; no G2a fields. Verifier `verify_g1b_rows.py` requires the verified G1a log and expects min(cap, G1a total) rows, the matching END reason, strictly increasing indices, first (and, when complete, last) index equal to G1a, TSV and canonical JSON re-read equal, first five rows equal to the D1 1350 log. For 1350 only the 1k script runs (938 < 1000); the 10k script is kept for larger traces and not run for form. Scripts `g1b-tlp-rows-1k.pevs` SHA-256 `952996AEAAA8EB30746F19541F4819FB378B6F78491E73558645CD6E08EA8249` and `g1b-tlp-rows-10k.pevs` SHA-256 `769F7142D33332C3A710F081602EF1048A7BA4F771F886A247F534A5E5F73A28`, identical deployed copies (v1 superseded). PASS claim: the row export mechanism works. |
| PCIe-G1c | Full-trace Row Export | PASS (2026-09-14, same run as G1b cited as evidence): `complete_export: true`, 938 of 938 G1a TLP callbacks exported, first/last index equal to G1a (1944516/2121703). Separate claim from G1b: every TLP callback of 1350 is exported. May cite the same 1350 1k-script run as evidence when its verifier summary shows `complete_export: true` (938 of 938, last index equal to G1a). The G1b-G1c capacity gate is satisfied for 1350 (938 rows, about 50 KB). |
| PCIe-G1d | Reproducibility | PASS (2026-09-14): second run on a fresh protected copy, `compare_g1_exports.py --expected-rows 938` returned PASS_REPRODUCED; rows.tsv SHA-256 `0028CC8D65948F0BCBF4149A7F50328DC815BDDB1B944F4684CE88F1EE45D3B8`, canonical rows.json SHA-256 `A5398FB6863F63CC44D809EFF2884E3EECE53D551B1FCA18414238C5EE0C12D6` for both runs; post-close identities unchanged. Criteria: fresh protected copy and reopened trace, rerun the same 1k script. PASS via `compare_g1_exports.py --expected-rows 938`: both runs 938 rows, identical packet index sequence, all columns equal row by row, identical TSV and canonical JSON SHA-256. Scope: all TLP callbacks of this subscription, not all PETracer events. |
| PCIe-G2a | Transaction Field Probe | PASS (2026-09-14, evidence `docs/pcie-g2a-evidence.md`): 938 rows equal to G1 export, zero runtime-error text, one END; VSE equals GUI for request 2097003 (CfgRd0: Tag 3, RequesterId 000:00.0, CompleterId/ComplStatus NA) and completion 2121703 (CplD: Tag 7, RequesterId 000:00.0, CompleterId 001:00.0, ComplStatus 0=SC); post-close identities unchanged. CompleterId/ComplStatus are null on all non-completion types and present only on 0x11/0x12; Tag/RequesterId are never null (including Msg), so G2b must select keys per TLP type. 0x11 completions include ComplStatus 1 (UR) rows, not GUI-checked and not interpreted. Design: `g2a-tlp-fields.pevs` (SHA-256 `DBE5ADB6AC4CD02FF73B013C69B5296D6262A7ED835ECADEBE0FA798E3C726FE`, identical deployed copy) reads `in.Tag`, `in.RequesterId`, `in.CompleterId`, `in.ComplStatus` for every TLP callback on 1350 and prints NA when a field reads null; no defaults, pairing or interpretation. `verify_g2a_fields.py` requires 938 rows equal in index/time/channel/type to the verified G1 rows.json, one END, zero runtime-error text, and reports per-type availability. PASS also needs VSE values equal to GUI for at least one request (packet 2097003 CfgRd0: RequesterID 000:0:0, Tag 3) and one completion (packet 2121703 CplD: RequesterID 000:0:0, Tag 7, CompleterID 001:00:0, Status SC), from the retained G1b GUI screenshots, plus unchanged trace/copy hashes. Known limit: a field may read 0 rather than null on types where it does not apply, so per-type applicability must not be inferred from non-null values alone. |
| PCIe-G2b-1 | TLP Role Classification | PASS (2026-09-14, offline from G2a fields.json; evidence `docs/pcie-g2b-evidence.md`): roles from the installed vendor constant table `VS_constants.inc` (SHA-256 `799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D`) checked against field shape; 1350: 439 NON_POSTED_REQUEST (CfgRd0 293, CfgWr0 64, MRd32 82), 417 COMPLETION_CANDIDATE (Cpl 70, CplD 347), 82 POSTED_OR_OTHER, 0 UNKNOWN. 0x9/0xE/0x12 GUI-confirmed; 0x11 vendor-constant only. |
| PCIe-G2b-2 | Request/Completion Association | PASS (2026-09-14): key (RequesterId, Tag), nearest preceding non-posted request, completions never close a request, no completeness/timeout/fault claims. 1350: 417/417 completions associated, 0 without preceding request, 0 multi-completion requests, all opposite direction; 417 requests COMPLETIONS_OBSERVED, 0 NONE_OBSERVED_IN_CAPTURE, 22 SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED (CfgRd0 19, CfgWr0 3); completion statuses SC 408, UR 9 (Cpl). Request 2097003 -> completion 2097005 also visible in the retained GUI screenshot. Independent cross-check (13:30-13:33): LeCroy Split transaction view groups 1945005 MRd(32) Tag 11 with a Cpl UR (Lwr Addr 0x028) as Split Tra 22 and 2093086 MRd(32) Tag 0 with a Cpl UR (Lwr Addr 0x01C) as Split Tra 29, matching the G2b association and excluding earlier same-key CfgRd0 requests for these two; the 22 reissued-key requests are not GUI-checked. |
| PCIe-G3a | Non-success Completion Candidates | PASS (prototype, 2026-09-14, evidence `docs/pcie-g3ab-evidence.md`): `g3_candidates.py` over G2b associations; one candidate per associated completion with status other than SC, interpretation NOT_EVALUATED, optional GUI cross-check reference. 1350: 9 candidates (MRd(32) -> UR), 2 with LeCroy Split transaction cross-check. Terminology (owner decision 2026-09-14): candidate detectors, not anomaly rules. |
| PCIe-G3b | Same-key Reappearance Candidates | PASS (prototype, 2026-09-14): one candidate per request whose (RequesterId, Tag) reappears before an associated completion was observed; reports first/repeated request, packet gap, and whether a completion was later observed for the key (attributed to the last request of the chain). No retry/timeout claim. 1350: 22 candidates at 4.848 sec. |
| PCIe-G3c-0 | Message Field Probe | PASS (2026-09-14, evidence `docs/pcie-g3c0-evidence.md`): END 938 TLPs, 3 message rows equal to G2a, zero runtime-error text, identities unchanged; 1945029 reads MessageCode 0x30 ERR_COR, MessageRoute 0x0 TOROOTCOMPLEX, matching the retained Split view (Link Tra 33); 2093072 also ERR_COR (not GUI-checked); 1944516 MsgD 0x50 SLOTPOWERLIMIT. Temporal adjacency to UR groups recorded only; causality NOT ESTABLISHED. Design: `g3c0-msg-fields.pevs` (SHA-256 `9389D6E2EE5A876D9A17576FD9F2A17F7220D62B58D7FA0DABDD7C95227B9B48`, identical deployed copy) emits Message TLPs only with RequesterId, `in.MessageCode`, `in.MessageRoute` (vendor-script field names), NA for null, and one END with TLP and message counts. `verify_g3c0_messages.py` requires END TLPs = 938, message rows equal to the 3 G2a message rows (1944516 0xE, 1945029 0xD, 2093072 0xD) in index/time/channel/type/RequesterId, and names codes from `VS_constants.inc` (ERR_COR = 0x30). PASS also needs packet 1945029 to read ERR_COR, matching the retained Split view screenshot (Link Tra 33, Msg To RC, ERR_COR, ACK #1945030), zero runtime-error text and unchanged identities. G3a/G3b are not changed; ERR_COR is not interpreted as a cause. |
| PCIe-G3c | Error-message Correlation | PASS (prototype, 2026-09-14, evidence `docs/pcie-g3c-evidence.md`): RISK KEPT: the 64-packet bound was chosen after seeing v1 results and is a prototype heuristic, not a proven PCIe rule; reports must carry this limit. `g3c_nearby_messages.py` attaches Message TLPs within 8 TLP rows AND 64 vendor packet indices of each candidate's anchor span (no timestamps); every attachment `temporal_correlation_only`, candidates stay NOT_EVALUATED, causality NOT ESTABLISHED. The 64-packet bound was added after v1 (rows only) attached ERR_COR across a ~148,000-packet stretch without TLPs; v1 output kept as `pcie-g3c-20260914-v1-rowonly`. 1350: 23 of 31 candidates have a nearby message, 9 attachments excluded by the packet bound (8 cross-gap, 1 at -450); each G3a UR candidate has exactly its own group's ERR_COR (1945029 or 2093072). |
| PCIe-G3d | Candidate Context Windows | PASS (prototype, 2026-09-14, evidence `docs/pcie-g3d-evidence.md`): `g3d_context.py` gives each candidate a primary LeCroy Go to Packet (G3a request, G3b first request), one block per anchor span (G3b: first and repeated request separately) with 5 TLP rows before/after (PRESENTATION_HEURISTIC), rows keeping packet index, raw packet gap from the previous TLP row, time, channel, type, RequesterId, Tag, CompleterId, status and G2b association, `TRUNCATED_AT_CAPTURE_BOUNDARY` where short, and G3c nearby messages copied not recomputed. No new candidates, ranking or interpretation. 1350: 31 candidates, 53 blocks, 4 truncated sides, 7 blocks visibly crossing the ~148,034-packet non-TLP stretch. Supersedes PCIe-G4. |
| PCIe-G3e | Candidate Grouping | PASS (prototype, 2026-09-14, evidence `docs/pcie-g3e-evidence.md`): `g3e_groups.py` merges only on shared anchor packet, shared G2b association lineage, or a G3a request/completion being another candidate's anchor (rules fixed before results); time, nearby message, context overlap, RequesterId, Tag and status are auxiliary only. 1350: 31 candidates -> 16 groups (12 multi-member, 4 singletons), every candidate exactly once, earlier outputs byte-identical, no group-count target, no severity/priority/interpretation. OWNER DECISION (2026-09-14): rule 2 kept unchanged (option 1); no post-hoc distance bound. The ~148,500-packet lineage span (G003, G009-G012) is surfaced in G3f instead. |
| PCIe-G3f | First Single-trace Triage Output | PASS (prototype, 2026-09-14, evidence `docs/pcie-g3f-evidence.md`): `g3f_findings.py` turns each G3e group into one finding answering where to look (primary and per-segment Go to Packet), what was observed, why surfaced, what is nearby (G3c messages, G3d context refs, GUI cross-checks) and what is not known. Groups are split into local segments by overlapping G3d context blocks (no new distance threshold, membership unchanged); multi-segment findings state that grouping does not establish one failure episode, with the packet span. Three issues found in the first run (unplaced messages, non-anchor rows listed as anchors, singleton wording) were fixed before delivery. 1350: 16 findings, all multi-segment, 0 unplaced messages; capture order, no ranking, NOT_EVALUATED. Supersedes PCIe-G5; PCIe-G6 ranking is DEFERRED. |
| PCIe-G7 | Single-Fail Markdown Report | PASS (prototype, 2026-09-14, evidence `docs/pcie-g7-evidence.md`): `g7_render_markdown.py` renders `findings.json` only, as a Traditional Chinese engineering report with PCIe names, packet identities and field names in English (owner decision 2026-09-14). Per finding: 建議先看, 觀察到什麼, 相關位置, 為什麼列出這一項, 目前還不能確定, 追溯. A repository report contract (order, all findings, Go to Packet, anchor packets, `UNKNOWN`, traceability, no over-claims, no dashes) fails closed before writing; human-writing skill principles only, `check_prose.py` advisory. 1350: `artifacts/reports/pcie-g7-1350-20260914/report.md`, 16 findings, 0 contract errors. Owner review 2026-09-14: wording patch v2 (候選檢查位置, 主要定位點, fixed-rule navigation note), analysis unchanged; v1 kept as `report-v1.md`. |
| PCIe-G8 | Single-Fail HTML Report | PASS (prototype, 2026-09-14, evidence `docs/pcie-g8-evidence.md`): `g8_render_html.py` renders the same `findings.json` with G7's shared wording as an offline, script-free page: top notice panel (UNKNOWN, no failure-cause judgement, 64-packet prototype heuristic, capture order, navigation-anchor note), scan table with badges (status, nearby messages, same-key, segment count and packet span), and 16 cards whose first layer shows the navigation anchor, summary and segments while `<details>` keeps all evidence, limitations and traceability. HTML contract fails closed; 1350: 16 cards, 0 errors. Next: first engineer trial. |
| PCIe-G9a | Offline Triage Runner | PASS (prototype, 2026-09-14, evidence `docs/pcie-g9-runner-evidence.md`): `scripts/pcie/run_pcie_triage.py` (wrapper `run-pcie-triage.ps1`) chains G2b, G3a/b, G3c, G3d, G3e, G3f, G7 and G8 from a verified extraction bundle input manifest, calling the existing stage CLIs. Excludes PETracer GUI, COM, `.pex` opening, VSE execution, legacy conversion, AI agent and writing skill (owner decision). 1350 run `20260914T081330Z-78474DEA`: all stages PASS, findings identical to the manual run, report.md differs only in the findings SHA line. |
| PCIe-G9b | Fail-closed Contract | PASS (prototype, 2026-09-14): stops on missing or hash-mismatched inputs, non-PASS verifier summaries, messages verified against another fields.json, TLP count mismatch, existing output directory, or any stage failure; writes `run-manifest.json` with `failed_stage`. Tested for each case. |
| PCIe-G9c | Engineer Review Package | PASS (prototype, 2026-09-14): package with report.html, report.md, findings.json, run-manifest.json (trace identity, input, script, stage and output SHA-256, parameters) and `使用說明.md` (Traditional Chinese usage, limits, feedback with run id and finding id). 1350 package `artifacts/reports/pcie-triage-1350-20260914/`. |
| PCIe-G9 | Engineer Review Build | NOT STARTED; one real Fail-named trace, which first needs F0i open/extraction qualification. Its filename stays a hint until the engineer confirms the failure context. Owner direction 2026-09-14: engineer trial of the G8 prototype may start in parallel with G9a-G9c; the runner is not a gate. The 1350 package is outcome-unknown, so a real Fail trace is still required for this slice. |
| PCIe-G10 | Signal Expansion | SUPERSEDED BY PCIe-B1 (2026-09-14): the trigger is met by engineer feedback on the hang package (TLP-only candidates do not answer RC-to-EP control or link questions). |
| PCIe-A1 | COM Automation Qualification | PASS (2026-09-14, owner unfroze COM for this probe only): `CATC.PETracer` -> `OpenFile` -> `GetVScriptEngine` -> `LaunchVScript` with `OnVScriptFinished`/`OnVScriptReportUpdated` events ran the existing `g1a-tlp-count` on a read-only 1350 copy with no GUI input; semantic result equals the GUI route (938 TLP, 1944516 -> 2121703, no runtime error), the G1a log verifier also accepts the event text, trace/source SHA unchanged, PETracer exited after `Close`. run1 was A1_PARTIAL only because the probe joined events without line breaks. COM is NOT part of the formal flow; GUI route stays the fallback. Not tested: hidden window, hang/legacy conversion, batch, G2/G3 scripts, export APIs. Next candidate slice A2 (hidden/background execution) needs an owner decision. See [A1 evidence](docs/pcie-a1-com-evidence.md). |

### PCIe Failure Timeline direction (owner decision 2026-09-14)

Engineer feedback on the hang package: the report "only says a Tag reappeared";
engineers need (1) whether RC control of the EP is reasonable and (2) whether
the link shows abnormal behaviour, e.g. before the BSOD at the end of the hang
trace. Decision: stop adding generic G3 candidate detectors; keep G2/G3/G7-G9 as
the generic TLP triage layer and add two analysis lines that end in one timeline:

- RC/EP register timeline (B2): trace values plus engineer-defined expectations
  give deterministic findings. AI may draft watchlists from engineer requests or
  permitted datasheets and may explain deterministic findings; it never produces
  register values, offsets or bit definitions, never calls something unreasonable
  without an explicit rule, and never claims root cause.
- Link/Data Link timeline (B1): LTSSM, link conditions, speed/width, DLLP
  ACK/NAK/PM, ordered sets, error flags, with objective rules only.

Field availability is taken from the installed VSE manual and `VS_constants.inc`
(`in.LtssmState`, `_PKT_LINK_CONDITION`/`in.LinkConditionType`, `in.Speed`,
`in.LinkWidth`, `_PKT_DLLP`/`in.DLLPType`/`in.AckNak_SeqNum`, `_PKT_ORDERED_SET`/
`in.OrderedSetType`, `_PKT_EIE_EVENT`, error flags such as `in.BadLCRC`, and
`in.Register`/`in.RegisterData`). These were manual-only candidates at roadmap
creation; current real-trace qualifications are recorded by slice below (B1a and
B2a). Probe evidence precedes parser or rule design.

| Slice | Name | Status and acceptance |
| --- | --- | --- |
| PCIe-B1a | Link Field Probe | PASS (2026-09-14, evidence `docs/pcie-b1a-evidence.md`): COM run on the hang converted copy, verifier `PASS_LINK_FIELD_PROBE_OUTPUT`, TLP count matches G1a (704). DLLP type/AckNak seq, ordered set type, link condition type, `LtssmState`, speed, width and `HasErrors` are populated; EIE delivered nothing. Window 225049-1484398 (TLP-free stretch) holds 21 LTSSM changes, 13 link-condition records, 2 speed/width changes and all 50 sampled error events; one NAK at 225042. Field verification only; codes not yet named. Route COM (`scripts/pcie/com_run_vse.py`); run1 failed on a VSE parse error and is kept. |
| PCIe-B1b | Case Window Extraction | PASS (2026-09-15, evidence `docs/pcie-b1b-evidence.md`): step 0 probed 52 engine constants; COM window export 225041-1484414 verified (`PASS_WINDOW_EXPORT`: 1,259,373 events in 33 segments, 22 LTSSM changes, 14 link conditions, 1 NAK, 4 TLPs equal to the G1 export). Reconstructed: Upstream LINK_DOWN at 9.512 sec; Downstream Recovery with LINK_UP/DOWN records to 9.575 sec; Downstream Polling (not valid) with 382,842 error-flagged TS1 to 9.600 sec; no delivered event 9.600-10.912 sec; Upstream LINK_UP, Polling, Configuration, Recovery and L0 on both channels at 10.912 sec before the last TLPs. Open: which error type `HasErrors` reflects (no individual flag set), per-channel counts, GUI cross-check of Up/Down wording, speed code labels. No MUX interpretation (B1d). |
| PCIe-B1c | Link Training Timeline | PASS (2026-09-15, commit `5febc84`, evidence `docs/pcie-b1c-evidence.md`): offline from the verified B1b timeline.json; 13 phases: Detect (Upstream), Recovery/link-condition phases (Downstream) to 9.575 sec, Polling (Downstream, 382,842 TS1 with HasErrors) to 9.600 sec, no observed events 1.312 sec, then Upstream LINK_UP, Polling, Configuration, Recovery and L0 on both channels at 10.912 sec. Unknowns printed (HasErrors subtype UNKNOWN, per-channel counts, Up/Down wording, speed labels); contract rejects judgement wording. |
| PCIe-B1c-x2 | HasErrors Subtype Probe | PASS as probe, subtype still OPEN (2026-09-15, evidence `docs/pcie-b1c-x2-evidence.md`): COM probe of 26 candidate members, totals match B1b. All 384,993 `HasErrors` events are Downstream TS1 (2 Recovery.RcvrLock, 382,842 Polling before the gap, 2,149 Polling after it); none of the 26 members is set. `TsErrorDataRate/Format/Parity/RsvdField`, `G3ErrorFraming`, `RsvdField` and the manual spelling `ErrorAllignment` are null on every event. Also established: window TS1 are Downstream (1,233,697 of 1,234,691), Upstream has 2,289 events, all after the gap except one. Next evidence for the subtype: GUI packet view of a flagged TS1 (with x1) or a raw TS field probe. |
| PCIe-B1c-r1 | Channel Attribution Revision | PASS (2026-09-15, evidence `docs/pcie-b1c-r1-evidence.md`): `b1c_training_timeline.py` takes the x2 and GUI evidence; each phase lists the last LTSSM state of each channel at its start, `HasErrors` gets a channel only when its whole x2 range is on one channel (basis printed, range sums checked), GUI labels appear only as marked samples. Post-gap phases now read: start Upstream, HasErrors on Downstream, Downstream still Polling. Base B1c output kept; revision in `artifacts/evidence/pcie-b1c-r1-hang-20260915/`. |
| PCIe-B1c-x1 | Link Condition GUI Cross-check | PASS (2026-09-15, evidence `docs/pcie-b1c-x1x3-evidence.md`): PETracer GUI shows Link Event "Link Down" at 225041 and "Link Up" at 1479760, matching the probed constants; the manual's swapped text is not what the analyzer displays. File identities unchanged. |
| PCIe-B1c-x3 | Flagged TS1 GUI Detail | PASS at sample level (2026-09-15, same session): flagged Downstream TS1 show analyzer Training Sequence errors: 1096918 and 1479761 `TSRsrvErr` (RSVD 0,1,0; data rate shows a Reserved bit; Link/Lane PAD, N_FTS 254); 990799 `TSDataRateErr, TSRsrvErr, TSLaneErr, TSTrainingControlErr`. Not established: that every flagged TS1 in the phases carries the same error (three samples viewed). |
| PCIe-B1d | MUX-aware Rules | COMPLETE for product-rule v1; bounded implementation/replay PASS (2026-09-30, `docs/pcie-b1d-evidence.md`, r1 rules / current r2 report): three owner-requested source/wording corrections validated. MUX_CONNECTIVITY uses Q7 bilateral valid training independently of BIDIRECTIONAL_L0's explicit valid L0 records; both PASS on this hang window, sampled x1 PASS. INITIAL_GEN1_SAMPLE is observation_only / INCONCLUSIVE (2.5 GT/s x1 observed before first valid L0, no engineer acceptance rule or spec verification). TARGET_SPEED_OBSERVED uses separate present/absent wording, remains INCONCLUSIVE; post-L0 config activity INCONCLUSIVE, initialization completion NOT_EVALUATED. 1.400 sec is descriptive and 384,993 HasErrors tolerance NOT_EVALUATED. Four validation debts (training timeout, TS-error tolerance, Gen3 convergence, hot-plug completion) remain non-blocking for closing v1. 21 focused / 138 PCIe tests passed; corrected two-run replay byte-identical, inputs unchanged. Prior B1d outputs remain superseded history; B1c results/historical UNKNOWN metadata preserved. No overall case PASS/FAIL, direct MUX measurement or root cause; B1e follows as a separate gate. Final r2 report has conservative L0 source attribution and corrected typography; JSON identical to r1, Markdown only those two edits. Local closure only, no commit/push/PR/merge. |
| PCIe-B1e | Link Findings | COMPLETE locally; validation PASS for bounded findings build (2026-09-30, `docs/pcie-b1e-evidence.md`): 12 B1d states/evidence preserved, expected context separated from rule mismatches, initial Gen1 observation-only, unknown evidence/thresholds not promoted. Real hang replay twice byte-identical with source hashes retained; 7 focused tests PASS. No rule mismatch on this input; no overall product PASS or root cause. Focus AFTER_BIDIRECTIONAL_L0. B2a next, no commit/push/PR/merge. |
| PCIe-B2a | Register Field Probe | COMPLETE locally; validation PASS for this converted non-Flit capture (2026-09-30, `docs/pcie-b2a-evidence.md`): two COM runs DONE, 704 TLP callbacks / 333 config-and-completion rows byte-identical; hashes, size, mtime and analysis-copy read-only preserved. Register is byte offset, 32 CfgRd / 29 CfgWr, first/last BE matched raw header, 59 DWORD payloads matched little-endian RegisterData (29 writes + 30 config returns). CfgRd requests carry no read value; unassociated CplD remains unclassified. 7 focused tests PASS; B2b next, no delivery. |
| PCIe-B2b | Config Access Log | COMPLETE locally; validation PASS for this capture (2026-09-30, `docs/pcie-b2b-evidence.md`, r2-run1 current): 61 accesses (32 reads / 29 writes), 30 qualified read returns, 0 after reconnect. Logs preserve byte masks, completion evidence and connection interval; unresolved key reuse never supplies read value. Full TLP keys retained; qualified config replies retire pending keys, avoiding late candidates attaching to completed config reads. 7 focused tests PASS, two-run outputs byte-identical. Initial outputs superseded, historical G2b unchanged. No timeout, applied-write or new-SDE state claim. B2c next. |
| PCIe-B2c | Capability / Register Resolution | COMPLETE locally; validation PASS for observed mapping (2026-09-30, `docs/pcie-b2c-evidence.md`): old device conventional chain 0x80 PCIe -> 0xE0 MSI -> 0xF8 PM -> end; LinkControl 0x90 / PMCSR 0xFC. Extended observed 0x100 -> 0x108 -> 0x110 L1SS -> 0x128 -> unobserved 0x200; L1SS controls 0x118/0x11C supported, full extended chain UNKNOWN. Public Linux v6.12 layout values independently checked; no full PCIe spec or product-rule verification. 5 focused tests PASS including variable offsets, cycles, missing nodes, completion timing and epoch isolation; two-run output identical. B2d next. |
| PCIe-B2d | Observed Config State | COMPLETE locally; validation PASS for separate last-read/last-write-intent byte views (2026-09-30, `docs/pcie-b2d-evidence.md`): Completion-time reads, BE-selected intent bytes, unknown bytes not zero, epoch/BDF isolation. 4 focused tests PASS after fixture/incorrect expected-value correction; two before-switch replays identical, new-SDE view empty/UNKNOWN. Last LinkControl intent 0x42 at packet 10354 (ASPM bits 2); no read-back/applied-state claim. B2e next. |
| PCIe-B2e | Snapshot Query | COMPLETE locally; validation PASS for observed query (2026-09-30, `docs/pcie-b2e-evidence.md`): offset/width query and capability-derived names, last read vs write-intent values/evidence, partial bytes UNKNOWN, later-write marker, cut/epoch isolation. 4 focused tests PASS; before-switch two-run JSON/MD identical, after-reconnect raw 0x90 query stays unnamed/UNKNOWN. No hardware snapshot claim. B2f next. |
| PCIe-B2f | Snapshot Diff | COMPLETE locally; validation PASS for observed comparisons (2026-09-30, `docs/pcie-b2f-evidence.md`): read and write intent compared separately, UNKNOWN never zero, same-epoch observed changes supported, MUX old/new epoch not comparable despite same BDF. Snapshot/source recomputation rejects tampering or identity mismatch; 5 focused tests PASS; real diff two-run JSON/MD byte-identical. B2g source/scope gate next. |
| PCIe-B2g | Product ASPM Policy / Watchlist | SOURCE/SCOPE GATE (2026-09-30, `docs/pcie-b2g-engineer-questions.md`): no product FAIL. Extraction/schema COMPLETE; evidence preparation COMPLETE; product evaluation WAITING FOR SOURCE/SCOPE. Current schema v2 in r1-run1 separates write intent, effective_state=UNKNOWN, expected_state=UNKNOWN and policy_result=NOT_EVALUATED. Packet 10354 is L1_ENABLE_WRITE_INTENT (0x42 / ASPM bits 2), not effective/system state, testcase violation or root cause. Minimum four engineer answers: side+device/epoch+BDF, phase, per-register bits/expectation/provenance, intent-vs-read-back/equivalent-proof acceptance. 5 preparation / 5 observed-state tests and 183 PCIe suite tests PASS; same BDF/offset/VID-DID epoch isolation regression added; v2 replay identical, raw observation fields/input bindings unchanged. B1d COMPLETE and B1e/B2a-B2f local completion retained; B2h conditional, B3 unstarted. No commit/push/PR/merge. |
| PCIe-B2h | Vendor Registers | CONDITIONAL; only with engineer-supplied GL9767 offsets, bit definitions and expectations permitted for tool use. No guessing. |
| PCIe-B2h-0 | Register-definition Framework (no vendor values) | MECHANISM PASS, SCHEME NOT FINAL (2026-10-05, owner asked to start the decode and CATC-feature work while vendor definitions are missing; evidence `docs/pcie-catc-decode-verification.md`, inventory `docs/catc-feature-inventory.md`): `scripts/pcie/catc_regdef.py` validates an engineer-supplied regdef (provenance and permitted-for-tool-use required), decodes B2b config accesses offline with byte-enable-aware UNKNOWN, and emits a CATC `.dec`. Offline PASS: 13 focused tests, 196 PCIe tests. PETracer 13.26 PASS for one case: the generated `.dec` (installed `CFG.dec` backed up, replaced, restored; SHA-256 `639AB3C0...0FF7` identical after every run; trace copy `C6E9646B...` unchanged) decodes CfgWr LinkControl at packets 8658/9915/10354 as ASPM 2/0/2 via COM `ExportToText` diff against a no-script baseline. Found and fixed one FAIL: `in.Data` is a big-endian bit stream. Known costs: an active script replaces CATC native config decoding (raw `Data` fallback only); CfgRd request has no data so reads are not decodable by `CFG.dec`. NOT VERIFIED: MEM/SDhost `.dec`, multi-byte and multi-register DWORDs, `.pecfgdec`. NOT ESTABLISHED: any vendor register meaning (no definitions), MMIO extraction. B2h itself stays CONDITIONAL until definitions arrive. |
| PCIe-B2h-1 | Native Configuration Space API Probe | PROBE PASS at sampled positions (2026-10-05, evidence `docs/pcie-b2h1-cfgspace-api-evidence.md`): the installed 13.26 Automation API `GetConfigurationSpace(bdf, packet)` returns CATC-decoded config state through COM with no GUI input and no install-folder change; on one trace, BDF 256, epoch before_disconnect, five packets, native state equals the B2b byte-level reconstruction (same known-byte sets, 0 mismatches, 48 to 115 bytes per packet). Scope of the claim: cross-check at sampled positions only, not independent truth for the whole extraction (equal snapshots do not prove every intermediate event, and both paths may share LeCroy export decoding). The original `.pecfgdec` acceptance items were NOT RUN; this is another viable path, not those items passing. `.pecfgdec` and `BuildConfigurationSpace` are out of the main line (owner decision 2026-10-05); no write to `CfgSpaceScripts`. |
| PCIe-B2h-2 | Read-only Sidecar Register Decode | PROTOTYPE PASS (2026-10-05, evidence `docs/pcie-b2h2-sidecar-evidence.md`): `scripts/pcie/b2h2_sidecar.py` decodes saved CATC snapshots with the existing regdef and shows CATC merged value, last write intent and last read-back as separate evidence with the native CATC field alongside; never promotes one into another. Five saved positions reproduce LinkControl unknown/unknown/2/0/2; unknown bits are never zero-filled and never influence decoded fields; packet boundary measured (write included at its request packet, read at its completion packet, selected packet inclusive, query order irrelevant, B2b makes the same call); out-of-scope epoch/device/trace refused with exit code 4. 214 PCIe tests pass; four deliberate implementation breaks were each caught. Not established: any vendor register meaning (no definitions; request drafted in `docs/pcie-vendor-register-request.md`), other epochs/traces/devices, MMIO. SDhost/MMIO deferred until the config decode architecture is chosen. |
| PCIe-B3a | Unified Event Contract | NOT STARTED; common event shape: packet, time, layer, type, device, details, evidence. |
| PCIe-B3b | Unified Timeline | NOT STARTED; RC config, TLP request/completion, DLLP and LTSSM/link events in one ordered timeline. |
| PCIe-B3c | Objective Findings | NOT STARTED; rule-backed only: expected MUX Link Down not reported; no L0 after Link Down, repeated Recovery, ASPM enabled under Disable ASPM, NAK/replay pattern, config sequence against the watchlist become candidates. |
| PCIe-B3d | Engineer Report | NOT STARTED; G7/G8 reports upgraded to three sections: RC/EP control timeline, link timeline, candidate findings. Completes Milestone 1 (Engineering Analyzer). |

Waiting-period slice proposal (2026-10-02): owner requested a slice plan first,
with one PR per slice, latest-head review and conditional merge before the next
slice. See `docs/pcie-waiting-period-slices-20261002.md`: existing local-only
B1d/B1e/B2a-B2g preparation require scoped delivery PRs; proposed new work is
B3a contract, B3b config/TLP timeline, B3b link integration, observation-only
Markdown, then HTML. No new implementation or PR started by this planning step;
B2g policy evaluation still waits for engineer source/scope/proof answers.

Engineer responses received via owner on 2026-09-30: this hang case is ASPM
disabled / SD7 insertion / device not visible / system hang / BSOD 0x124;
0xA0 belongs to other tests. Responder identity and actual response date remain
unspecified; see the B1d questionnaire. B2a-B2f now supply field/config/state
evidence; open for B2g: which registers/bits
are checked for RC control order, device BDF, case-specific registers, and a
register definition the tool may use (`0x940h[1]` is a supplied statement,
not yet a register decode contract). B1d's four missing quantitative/completion
criteria are validation debt, not blockers for its product-rule v1.

Milestones (owner direction 2026-09-14): Milestone 1 Engineering Analyzer ends at
PCIe-B3d and tells engineers objectively what the RC did, how the EP answered and
how the link changed, without AI. Milestone 2 AI-assisted Analyzer covers C and D.
Existing TLP extraction, association, reports, offline runner and COM automation
are kept. Order: B1a, then B1b; no full AI layer or full register parser before
real evidence shows what the data looks like.

### Three-layer target and AI Research layer (owner direction 2026-09-14)

Engineer expectation, relayed by the owner: the tool organizes objective trace
facts, then AI researches PCIe, Root Complex/Root Port, Windows/WHEA, AER and
driver recovery material to point out where observations differ from normal
behaviour and which directions are worth checking. Target shape:

1. Evidence layer (VSE + Python, deterministic): RC-to-EP actions, register
   values, request/completion, DLLP ACK/NAK, LTSSM/link events, ERR_COR/AER.
2. Rule layer (deterministic): explicit rules and engineer-defined expectations
   only, qualified by product context.
3. AI Research/Hypothesis layer: reads layer 1/2 outputs plus product context,
   consults cited external sources, proposes candidate explanations labelled as
   hypotheses and lists the evidence still missing. Engineers decide root cause.

This supersedes the earlier blanket "no AI root-cause" freeze only as far as
cited hypotheses go: AI still never asserts root cause, never generates trace
values, and every hypothesis must cite evidence records and external sources.
The G9 offline runner keeps excluding AI; layer 3 is a separate stage.

Product context recorded as stated by the engineer (via owner, 2026-09-14), not
verified from a trace: on SD/SDE insertion or removal a MUX switches the PCIe
path, the old link goes down and a new link trains. Rules therefore must not
flag Link Down alone as abnormal for this product; what matters is whether the
link returns to L0 and whether Root Port/OS error recovery starts (PCIe-B1d). Whether
the hang trace shows this sequence is open until B1b/B1c; B1a does not interpret it.

| Slice | Name | Status and acceptance |
| --- | --- | --- |
| PCIe-C0 | Data Boundary | NOT STARTED; must precede every AI step. Candidate allowed for external AI/web: LTSSM sequences, standard PCIe registers, error codes, anonymized timelines, Windows stop codes. Candidate excluded: complete .pex, customer names, NDA register definitions, customer platform identity, internal confidential data. Owner/company policy decision. |
| PCIe-C1 | Evidence Packet | NOT STARTED; Python-built minimal packet (product context records with source/date/who stated, trace link evidence, RC activity, register changes, errors); AI never receives the .pex. |
| PCIe-C2 | Source Policy | NOT STARTED; fixed allowed sources (PCIe material, PCI-SIG authorized source if available, Microsoft WHEA/Windows docs, Root Port/AER docs, permitted internal knowledge); every hypothesis cites sources. |
| PCIe-C3 | AI Research | NOT STARTED; per investigation direction: reason, trace evidence ids, external sources, still unknown. Uncited hypotheses or root-cause claims fail a contract check. |
| PCIe-C4 | Hypothesis Report | NOT STARTED; report section of AI investigation directions, labelled hypothesis only. |
| PCIe-D1 | Case Manifest | NOT STARTED; engineer-supplied trace, scenario (operation, mux_switch_expected), expectations (e.g. aspm disabled), device BDF. |
| PCIe-D2 | Copilot Orchestration | NOT STARTED; one request runs trace check, converted disposable copy when needed, COM/VSE, B1, B2, B3, deterministic findings, C1, C3, MD/HTML. |
| PCIe-D3 | Engineer Review | NOT STARTED; engineer receives facts, rule results, AI investigation directions and citations, and decides root cause. Completes Milestone 2 (AI-assisted Analyzer). |

G1 status (owner decision 2026-09-14): CLOSED. G1a-G1d PASS for 1350: all 938 TLP callbacks of the subscription exported, reproducible, GUI-sampled.

Execution order (owner decision 2026-09-14): F0f-1 (PASS) -> G1a -> G1b ->
G1c -> G1d -> G2a -> G2b. G1 uses the already verified GUI path; COM stays
outside it so a failure cannot be confused between traversal, VSE and control
plane. G1a runs at the next session with PETracer in the foreground.

G1b-G1c capacity gate (owner decision 2026-09-14; a decision, not a code slice):
estimated full-export size = G1a total TLP callback count x G1b measured log
bytes per row, plus header/output overhead, judged together with the measured
10k runtime. If full export through the VSE output window and Save Output is
reasonable, proceed to G1c; otherwise redesign chunking/output path before G1c.
G1b PASS alone never starts a full export.

G3 prerequisite candidate, not scheduled: precise timestamp probe (candidate
API `Time2` components from the VSE manual, unverified). Trigger only if a
time-window/timeout anomaly rule is selected for G3. It is not part of G1b or
G2a; vendor display time such as `4.848 sec` is sufficient for row identity,
full export and approximate GUI navigation.

Recorded at the decision, not yet resolved:

- `S0-Remove SD7-1329-Fail.pex` has never been opened, so its legacy-format
  status is UNKNOWN. F0i is promoted to a G9 prerequisite; a format-update
  prompt stops it and starts separate P4a on a disposable copy.
- Vendor scripts such as `trans_1-1_TXN_BFT_RequestCompletion.pevs` and
  `trans_1-2_TXN_BFT_CompletionTimeout.pevs` are compliance tests driven by a
  test-stage/device-emulator context. They were not run and are field-name
  references only, not reusable triage rules.
- Full-trace runtime and output volume are unmeasured. In both 1350 and 1335
  the first TLP already carries a vendor event index near 1.9-2.0 million.

### Independent single-trace inspection branch (F0)

This owner-authorized presentation branch uses already verified Trace A evidence
and proceeds independently of E1a. It does not establish a device verdict,
diagnostic usefulness, or full-trace coverage, and it does not move the E1a
ground-truth gate. The inspection observation schema is PCIe-only and local to
this report; it does not replace the later F1 finding contract or establish a
USB/PCIe schema. The retained preview is in
[`artifacts/reports/pcie-inspection-1350-20260912`](artifacts/reports/pcie-inspection-1350-20260912/report.md).

| Slice | Scope | State |
| --- | --- | --- |
| F0a | Single-trace structured observation contract | PASS: inspection-only schema; no PASS/FAIL or finding semantics. |
| F0b | Convert retained extractor output to structured data | PASS: verified VSE log, input identities and five GUI rows bind into `observations.json`; no new VSE execution or trace parsing. |
| F0c | Markdown inspection report | PASS: rendered from the saved structured JSON. |
| F0d | HTML inspection report | PASS: same JSON source, offline and script-free. |
| F0e | Single-trace UX review | REVISION_READY_FOR_REVIEW: owner feedback on 2026-09-13 said the first report was hard to understand; plain-language revision is available, with engineer UX feedback still pending. |
| F0f | Bounded two-trace HTML comparison | IMPLEMENTED / REAL-PAIR NOT GENERATED: accepts two compatible F0 observation JSON files and compares per-trace first-five TLP type-code counts plus separately displayed rows. No cross-trace event/time alignment, PASS/FAIL result, or diagnosis. The requested 1329/1335 pair lacks completed F0 observations. |
| F0f-1 | Comparison semantics hardening | PASS (2026-09-14): fixed title `PCIe Trace Inspection Comparison`; Observed / Not established sections; sample-boundary note adjacent to the composition table; A-B difference column removed; outcome-like filename tokens shown only when present, as hints. Presentation only; input validation unchanged. |
| F0g | 1335 GUI evidence recovery | NOT STARTED / SIDE BRANCH: one clean screenshot at packet 2000010 recording visible, intervening and next-TLP indices with SHA-256; reuse the existing log, no extractor rerun; post-close hash check. Schema v1 is not relaxed (owner decision 2026-09-14). |
| F0h | 1335 observation materialization | NOT STARTED / SIDE BRANCH; after F0g PASS, existing builder with an E:-path manifest. |
| F0i | 1329-Fail open and bounded extraction qualification | NOT STARTED; PCIe-G9 prerequisite. Filename is a hint only; a legacy-format prompt means STOP and separate P4a. |
| F0j | Unlabeled pair comparison report | NOT STARTED / SIDE BRANCH; after F0h and F0i, titled as an inspection comparison, not PASS/FAIL. |

This sample labels extraction `PASS_BOUNDED`, ground truth `UNKNOWN`,
diagnostic result `NOT_EVALUATED`, and coverage as the first five TLP records
only. Renderer mechanics may inform later work; F1 fields and diagnostic
semantics remain gated by E3e and their own evidence.

F0f is a descriptive presentation utility only: it reads two existing
single-trace observation JSON files, does not open or parse `.pex` files, and
does not replace the E1a/E1b gate. A real comparison HTML is not available for
1329/1335 until both traces have eligible F0 observations; 1329 has no
extraction evidence, and its filename is not ground truth.

The initial 2026-09-12 report is preserved as the committed baseline. Owner
readability feedback on 2026-09-13 was that it was hard to understand. A
separate revision puts the plain-language purpose, bounded result and
non-claims first, with detailed fields and identities below; it changes no
observations or diagnostic semantics. F0e remains open until a reader reviews
the revised presentation.

D1e is closed as PASS within the five-record projection: the unchanged
extractor produced TLP output for Trace B, five records were sampled against
the B trace GUI, the analyzer was closed, and source/working-copy identities
remained unchanged. The earlier GUI-focus interruption is retained as
historical evidence, not the current slice state. See the final D1e closure in
the [staircase evidence](docs/pcie-staircase-evidence.md) and [handoff](docs/pcie-engineer-handoff.md).

Continuation input check (2026-09-12): read-only `Get-ChildItem` confirmed the
eight GL9767 captures still have the recorded sizes. `rg --files` beneath the
owner-authorized `C:\Users\reiko\Desktop\Kent` tree found zero matching
companion files with extensions md/txt/csv/xlsx/xls/pdf/docx/log/json/html/png/jpg.
This is a bounded accessible-files search, not proof that no evidence exists
elsewhere. ZIP files and installer payloads were not opened. No source hash,
runtime execution or prior PASS was requalified by this metadata-only check.

Needed only at E1a: PASS trace, PASS observed behavior, FAIL trace, FAIL
observed behavior. Trigger/operation and expected behavior are useful context;
root cause is not required. These are not D1e prerequisites. A fixed D1
projection does not establish full-trace coverage, precision timing or the
necessary V1 event model. E1b+ and integrated V1 testing remain NOT STARTED.

### Slice acceptance and boundaries

Each slice has a distinct evidence record. A failed or inconclusive prerequisite
stops the sequence at that slice; an available later task is not a workaround.
Successful sample execution is a runtime-path result, not a PASS judgment about
the captured device. No blanket PCIe-P0 qualification follows from this table.

| Slice | PASS evidence | Explicit exclusion |
| --- | --- | --- |
| B1 Trace Open Baseline | The installed PETracer.exe accepts a known-source candidate working copy, completes loading to a usable state with visible/navigable packet/timeline/detail content, gives no incompatible/unsupported/corrupt rejection, and evidence identifies the exact input. | No VSE, packet analysis or extraction; file existence does not imply known-good. |
| B2 VSE Entry Discovery | With the B1 trace loaded, record an actual, repeatable GUI path to the VSE script execution dialog/list. | No script run, COM research or undocumented API guesses. |
| B3 Vendor Sample Execution | Run one unchanged installed vendor sample, such as examp_tlps.pevs, through B2's entry; observe and retain output, dialog, file or log evidence attributable to that run. A parse/runtime error is not success. | No vendor sample edits, own script, structured extraction implementation or host bridge. |
| B4 Minimal Execution Evidence | Record executable, source/copy, sample identities, exact B1-B3 steps and observations; repeat from a closed trace/new protected copy and reproduce loading, entry and sample execution a second time. | No automation or extraction implementation. |
| C1 Own Minimal Script | The staircase separately proves bootstrap, fixed message, normal termination with zero runtime errors, then fresh-copy repeatability. | No trace-field reads or event extraction; DONE with an error is FAIL. |
| C2 Read Trace Primitive | At least one vendor API trace/event value is observed with trace and script identity, distinguishing data access from C1's fixed message. | No complete data model or multi-class extraction. |
| D1 Extraction Spike | One selected PCIe event class is extracted with a checkable trace/event reference and field/unit meaning. | No three-class implementation or common schema. |
| D2 Extraction Expansion | Extend only to a PCIe event set justified by actual API/trace evidence; repeatable records preserve identity and field/unit meanings needed by the chosen analysis. | No report UX; USB event names alone do not establish PCIe equivalence. |
| E Integration | Real PCIe extraction feeds a specified analysis flow with validated input semantics and a replayable result. Existing USB scorer reuse requires evidence of compatible meanings. | No governance expansion, speculative architecture or automatic core/common-schema adoption. |

### P0-B1 — retained execution contract

Question: can the installed PCIe Protocol Suite open a known-source candidate
PCIe trace? This does not claim prior decoder compatibility, known-good data
or a verified PASS/FAIL capture label.

- Owner-authorized trace source root: `C:\Users\reiko\Desktop\Kent`.
  Input candidate: `ASUS NV CRB_20260604\GL9767\S0-Remove SD7-1350.pex`
  beneath that root, from the existing sample inventory. File existence and
  size (105,224,486 bytes) were checked during planning; this is not a trace-open
  result. It is the smallest candidate in that inventory;
  that is a selection convenience, not a correctness or quality judgment.
- Before opening: verify the selected source against its recorded identity;
  create a fresh external read-only working copy and record both paths,
  SHA-256, size, UTC mtime and attributes. Use the baseline's actual
  `PETracer.exe` path and record the executable identity for the run.
- Operation: open only that working copy in PETracer. Observe successful load
  and a usable trace view. Record elapsed loading time and an image or equally
  concrete observation binding the visible content to the selected file.
- PASS requires loaded trace content, responsive GUI, no format/version/corrupt
  rejection, and unchanged source/copy identity after closing the trace.
  Merely launching an application shell or seeing a filename is insufficient.
- FAIL: explicit open/format/version/corruption rejection, crash, or evidenced
  hang. Record the exact observed message/behavior. Do not infer incompatibility
  from a slow load alone. Loading still in progress or unavailable GUI evidence
  is inconclusive, not PASS; missing/mismatched input is a prerequisite blocker.
- If input integrity changes or read-only handling is rejected, stop and record
  it. Do not retry against the original or silently make the copy writable.
- UNKNOWN after B1: VSE GUI entry, vendor/own .pevs execution, extraction and
  COM necessity. These are not B1 acceptance requirements.
- Close the B1 evidence gate before any B2 work. Under the owner's subsequent
  continuation instruction, PASS proceeds to B2; FAIL/BLOCKED stops immediately.
  Do not debug the installer or investigate another implementation as a workaround.

### Deferred PCIe event and integration decisions

The proposed later `LINK_CMD / LTSSM_STATE / LFPS` set matches the current USB
extractor's `_USB3_LINK_CMD`, `_USB3_LTSSM_STATE` and `_USB3_LFPS` selections in
`scripts/m2-packet-extraction-4.vse`. The C5 scorer directly consumes these
classes in `tools/discover-c5-suspicious-regions.ps1`. This is repository
evidence of USB-specific behavior, not evidence of PCIe field equivalence.

Retain D1/D2/E as future goals. Their exact PCIe event set and integration
contract remain unresolved until C2/D1 supplies applicable evidence. Do not
rename PCIe data to satisfy the USB schema or manufacture absent event classes.
This dependency does not block earlier runtime gates. Investigate it only when
the applicable staircase prerequisites have passed, not as a fallback task.
COM/Automation and a minimal host remain conditional on an observed runtime need;
no current slice requires them simply because the package contains support.

## USB milestones

| ID | Milestone | Status | Exit evidence |
| --- | --- | --- | --- |
| M0 | Repository bootstrap | Ready | Repo structure, scope, reference policy, and fixture policy exist. |
| M1 | Minimal VSE execution and host-owned summary bridge | PASS; historical anomaly recorded | A real `.usb` trace completes the selected VSE traversal, sends the required summary once through `NotifyClient()`, and the host produces a verifiable artifact with controlled integrity qualification. |
| G0 | Governance topology decision | Decision recorded: Minimal Audit + Lightweight Memory | The consumer decision is recorded from the Before/After evidence; runtime capability remains explicitly bounded. |
| G0-C1 | State authority correction | Controlled fresh-context behavior PASS; delivery tracked in Git | Memory alone did not reopen PASS in one isolated sub-agent case; not a universal recovery claim. |
| M2 | Packet extraction | M2-PACKET-EXTRACTION-1 through M2-PACKET-EXTRACTION-3 PASS; broader coverage not complete | Bounded selected decoded events cross VSE -> COM -> Host with event identity, selected protocol fields, JSON read-back, and controlled trace integrity. |
| M2-4 / DEMO-1 | Unified timeline and PASS vs FAIL candidate comparison | QUALIFIED for controlled source-preserving read-only mode | One combined extractor produces normalized timelines for PASS/FAIL candidates, reports a common-anchor candidate divergence without claiming absolute first divergence, and preserves the immutable source artifact. |
| DEMO-2 | One-click PASS/FAIL runner | Implemented; integrity closure PASS; Windows PowerShell 5.1 compatibility PASS | One command creates read-only sandbox copies, runs both extractions, compares timelines, verifies source and working-copy integrity, and writes JSON plus Markdown artifacts. |
| DEMO-C2 | Reliable common-anchor gate | PASS for fail-closed behavior on the known pair | Weak or insufficiently contextualized anchors are rejected; `NO_RELIABLE_COMMON_ANCHOR` produces no GUI recommendation. |
| DEMO-C3 | Timestamp fidelity | PASS | VSE seconds/nanoseconds survive the VSE -> COM -> Host -> JSON path with 0 ns error for the expert-labeled FAIL timestamp; comparator logic is unchanged. |
| DEMO-C4 | Semantic alignment | PASS for fail-closed behavior; useful alignment not proven | A verified raw-field and relative-gap fingerprint is unique in FAIL but has no PASS match, so `NO_RELIABLE_SEMANTIC_MATCH` is emitted and no GUI handoff is produced. |
| DEMO-C5 | Automatic suspicious-region discovery | PASS for the known pair; generalization not proven | Without a ground-truth input, PASS baseline scoring ranks a FAIL window intersecting the expert-labeled region at Top 1; the result remains triage evidence only. |
| DEMO-V1 | Engineer HTML report | PASS for presentation layer | Existing C5 JSON is rendered as a single offline HTML report with Top-3 candidates, exact timestamps, reasons/features, PASS/FAIL overview, integrity, and claim boundary. The JSON remains canonical; scoring is unchanged. |
| DEMO-V2 | Engineer-first triage report | PASS for presentation layer | Adjacent C5 windows are grouped into suspicious episodes; the report foregrounds the actionable interval, quantitative PASS baseline comparison, and claim boundary while retaining JSON as canonical. C5 scoring is unchanged. |
| DEMO-V3 | Evidence timeline | PASS for presentation layer on the known pair | Existing timeline events are visualized at their actual positions inside the primary episode; trace basenames are shown and exact internal metadata remains in details. Missing event-position data fails closed to a clear fallback message. |
| DEMO-V4 | Plain-language triage summary | PASS for presentation layer on the known pair | The Hero adds a conservative observation summary; selected LTSSM timestamps are labelled; secondary candidate scores stay in details; raw LFPS duration and baseline direction are easier to scan. C5 JSON and scoring are unchanged. |
| DEMO-V5 | Instrument color semantics | PASS for presentation layer on the known pair | Graphite surfaces, instrument blue, investigation amber, and integrity green now have distinct meanings; LFPS, LTSSM, and LINK_CMD use separate timeline colors. Layout, C5 JSON, and scoring are unchanged. |
| DEMO-V6 | Plain-language report copy | PASS for presentation layer on the known pair | The first screen leads with plain-language findings and next action; protocol names remain as secondary labels; p95, ranking details, and technical limits stay in expandable details. C5 JSON and scoring are unchanged. |
| DEMO-V7 | Capability/method/limit copy | PASS for presentation layer on the known pair | The report separates what the tool can do, how it works, and what it cannot claim; the Hero uses direct LFPS wording and secondary candidate ranking data stays hidden by default. C5 JSON and scoring are unchanged. |
| M3 | Transfer reconstruction | Not started | Control/bulk/interrupt/isochronous transfer grouping replayed and checked. |
| M4 | Enumeration analyzer | Not started | Reset-to-configuration sequence checks with bounded findings. |
| M5 | Large-trace performance validation | Not started | Trace size, event count, runtime, peak memory, and output size recorded. |
| M6 | Automation API integration | Not started | Repeatable open-trace/run-VSE/collect-result flow. |
| M7 | AI-assisted diagnosis | Not started | Optional explanation over normalized deterministic evidence. |

## Architecture decision: M1-B host-owned artifacts

The product requirement is an external, verifiable analysis result. It does
not require the VSE script itself to own Windows filesystem output. The
selected M1 architecture is:

```text
.usb trace
    -> LeCroy decoder/VSE
    -> deterministic event counters and findings
    -> NotifyClient()
    -> Automation host
    -> summary.json / summary.md / later triage artifacts
```

The earlier VSE-owned `OpenFile()` route remains recorded as a non-blocking
compatibility investigation. Its physical filesystem effect was not observed
in the local 10.40 Automation context, but that does not block the host-owned
route.

`M1-COM1` proved a bounded first-event VSE-to-host bridge. `M1-COM2` proved
that the known full-trace counters can cross that bridge once and match the
existing `trace-info.vse` baseline. `M1-COM3` added only host-side JSON
serialization and passed the artifact write/read-back acceptance. The run also
exposed an unexplained change to the input trace file, so the repository cannot
yet be declared a clean baseline. `M1-I1` repeated the relevant open/close,
VSE, and separate-output combinations on sacrificial copies without
reproducing the mutation. `M1-I2` then repeated the exact same-folder COM3
layout on a fresh sacrificial copy and also preserved the input identity.
M1 is now functionally qualified; the historical discrepancy remains recorded
as `UNEXPLAINED / NOT REPRODUCED`.

## G0 governance topology decision

The Before/After experiment established that static audit adoption can add
baseline identity, a contract, claim/scope guidance, and drift/readiness
visibility without changing M1 product behavior. It did not establish runtime
governance value.

This slice is a consumer-repository adoption decision, not an
ai-governance-framework task.

### Decision

The consumer decision is:

yaml:
  static_audit_adoption: BENEFICIAL_WITH_COST
  full_governance_value: INCONCLUSIVE
  G0_RESULT: RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY
  runtime_governance: NOT_ADOPTED
  runtime_readiness: PARTIAL_BY_DESIGN
  automatic_memory: NOT_CLAIMED

This is a LeCroy repository adoption decision, not an
ai-governance-framework task.

### Lightweight project memory

Keep a small, manually maintained project memory with only:

- current_goal;
- current_status;
- important_decisions;
- verified;
- not_verified;
- known_issues;
- next_step.

For the current project, this records M1 PASS, the verified trace-to-JSON
evidence, the historical mutation as UNEXPLAINED / NOT REPRODUCED, and M2 as
the next product slice.

### Explicitly excluded

Do not add these capabilities as part of G0:

- automatic stop/session memory writes;
- closeout receipts;
- memory authority or promotion chains;
- record-identity hashing;
- pressure state machines;
- full hook enforcement;
- autonomous memory consolidation.

### Established evidence

- M1 BEFORE: PASS.
- M1 AFTER: PASS.
- Product regression: 0.
- Product code mutation during adoption: 0.
- Static audit surface: established.
- Drift/readiness gap detection: established at adoption time by a manual run.
  Since 2026-09-14 the drift workflow is manual-only and automatic enforcement is
  disabled (see G0 lightweight maintenance); no automatic drift protection is claimed.
- Limited fail-closed case: observed.
- Runtime governance, hooks, memory continuity, and independent verification:
  not proven.

### Decision rule and boundary

Choose Runtime-Capable Mode only if LeCroy has a concrete, observable runtime
failure that this capability would address at worthwhile cost. Do not select it
merely because readiness is false or because the copied audit surface is not
self-contained.

After this decision:

- M2 is the next separate product slice, but this update does not start it.
- Missing runtime, hook, memory, or version surfaces remain findings, not
  implementation tasks.
- No Governance framework files are changed.
- Automatic memory is not claimed.

The first VSE script is intentionally a probe, not a parser. It requests all channels and trace events, counts the events delivered to `ProcessEvent()`, records trace and callback time boundaries, and records coarse channel and level buckets. The selected architecture sends the machine-readable result to the host rather than requiring VSE-owned file output.

The M1 claim ceiling is:

- `SUPPORTED`: the repository contains VSE probes using the locally observed lifecycle, event-delivery, and `NotifyClient()` primitives.
- `PROVEN`: the known real `.usb` trace completed the COM2 traversal and delivered the required four counters once to the host.
- `PROVEN`: host-side JSON serialization and read-back verification for the known trace.
- `PROVEN`: I1 sacrificial-copy A/B/C runs preserved input hash, size, and UTC mtime.
- `QUALIFIED`: I2 exact same-folder COM3 reproduction preserved input hash, size, and UTC mtime.
- `RECORDED`: the original input `.usb` size/timestamp change remains `UNEXPLAINED / NOT REPRODUCED`.
- `UNKNOWN`: whether the delivered-event count equals all events in every trace/version/configuration.
- `OUT OF SCOPE`: packet schema completeness, transfer reconstruction, analyzer correctness, large-trace performance, automation, and AI diagnosis.

### G0 lightweight maintenance (2026-09-14)

Owner-approved consumer maintenance; the G0 topology decision is unchanged
(`RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY`, runtime governance NOT_ADOPTED).

- Governance Drift workflow: **manual-only; automatic enforcement disabled.** The
  push/pull_request triggers were removed and only manual dispatch is kept. The job calls `governance/governance_tools/governance_drift_checker.py`,
  which was never vendored; all five runs since adoption failed with `[Errno 2]` and
  never evaluated drift. Even a manual dispatch fails until a pinned checker is vendored;
  restore triggers only after that. Comments in `AGENTS.base.md` (hash-protected) and
  `.governance/baseline.yaml` (generated) that mention drift checks or CI blocking describe
  the framework design, not active enforcement in this repository.
- Memory: `memory/01_active_task.md` is now a pointer to this PLAN (it had stayed on the
  USB C5 next step while the mainline moved to PCIe-G, the stale-handoff risk fixed by
  G0-C1). `memory/02-04` template placeholders are marked unused.
- Finding kept as history: `memory/2026-09-11.md` was written with the canonical writer
  and a `record_identity` hash although G0 excludes record-identity hashing. It is not
  rewritten; it is not repeated.
- `AGENTS.md` memory router: the referenced `governance_tools` commands cannot run in
  this repository (`python -m governance_tools.memory_workflow` fails: module absent). A
  consumer note records this and the G0 memory scope; the router text is not deleted.
- Framework M1 (ai-governance-framework PR #177, 2026-09-14) was reviewed. It clarifies the
  canonical memory Definition Of Done (memory update, session closeout and Git delivery
  are separate). This repository does not use that workflow, so the governance payload is
  not re-synced; only the reporting principle (local completion vs delivery vs push
  authorization) is added to `AGENTS.md` as wording. The framework's pending report-only
  `closeout_companion_not_observed` check would flag most product commit ranges here and
  is not adopted.
- Re-evaluate only if engineer use (PCIe-G9), a second contributor, or a claim-inflation
  incident creates a concrete runtime need.

## Rules for advancing

1. Keep each milestone a separate, reviewable slice.
2. Consume fields already exposed by LeCroy; do not reimplement the LeCroy decoder.
3. Do not commit vendor samples or trace captures without an explicit license/handling decision.
4. Use a known trace and retain replayable observations for every runtime claim.
5. Do not add AI, RAG, agents, or plugin abstractions before deterministic extraction has passed a real replay.

## M1 runtime record

For the first successful run, record at least:

```yaml
trace: <external path or redacted identity>
application: Teledyne LeCroy USB Protocol Suite
application_version: <observed version>
script: scripts/hello/trace-info.vse
output: host-owned artifact path, or `NONE` for bridge-only probes
process_event_calls: <observed count>
script_result: <observed result>
runtime: <measured duration>
```

The COM2 record is in `scripts/io-probe/real-summary-notify-results.md`, the
COM3 record is in `scripts/io-probe/host-summary-json-results.md`, the I1
record is in `scripts/io-probe/trace-integrity-isolation-results.md`, and the
I2 record is in `scripts/io-probe/exact-com3-integrity-results.md`. M1 is
functionally PASS; M2-PACKET-EXTRACTION-1 and M2-PACKET-EXTRACTION-2 are now
complete bounded extraction slices.

## G0 governance adoption boundary

G0 was evaluated only after M1 had a real-trace PASS. It remains separate from
the VSE feasibility experiment so failures can be attributed to the correct
layer.

```yaml
canonical_source: https://github.com/Gavin0099/ai-governance-framework
product_baseline_commit: bd93629e6c5241cc42df76ac366d14c97157ac78
framework_commit: 77262a51d79c1c6a1b5eff55ce3f4a64f5af3f37
local_dirty_checkout: E:\BackUp\Git_EE\ai-governance-framework
adoption_status: STATIC_AUDIT_SURFACE_APPLIED
topology_decision: RETAIN_MINIMAL_AUDIT_WITH_LIGHTWEIGHT_MEMORY
runtime_governance: NOT_ADOPTED
runtime_readiness: PARTIAL_BY_DESIGN
automatic_memory: NOT_CLAIMED
lightweight_memory: MANUAL_PROJECT_NOTES
```

The G0 experiment used a clean checkout derived from the GitHub source, pinned
the exact framework commit, reviewed the dry-run, and applied the adoption as a
separate commit. The dirty local framework checkout was not used.

G0 adoption artifacts do not by themselves prove runtime governance, hook
execution, fail-closed behavior, or memory continuity. Those require separate
runtime evidence. Do not turn those evidence gaps into implementation work
until the consumer-owned topology decision justifies that cost.

## M2-PACKET-EXTRACTION-1 result

The first M2 slice extracts only the installed LeCroy decoded event
_USB3_LINK_CMD from _USB3_TX and _USB3_RX. It exports event index, timestamp
text, and event type through the existing VSE -> COM -> Host path.

The batched transport result is recorded in
scripts/m2-packet-extraction-1-results.md. This slice does not claim complete
packet extraction, suspicious regions, root cause, comparison, GUI guidance,
or AI explanation.

## M2-PACKET-EXTRACTION-2 result

The second M2 slice extracts the installed LeCroy decoded event
_USB3_LTSSM_STATE. It exports event index, timestamp text, and event type
through the existing batched VSE -> COM -> Host path. The state name is not
exported because no reliable decoded state field was established for the
installed 10.40 environment; no state mapping is inferred.

The execution record is in
scripts/m2-packet-extraction-2-results.md. It records 30 target events,
matching Host reconstruction, JSON read-back, and unchanged sacrificial trace
integrity. M2 now has two completed post-G0 product slices; the third slice is
recorded below.

## M2-PACKET-EXTRACTION-3 result

The third M2 slice extracts the installed LeCroy decoded event _USB3_LFPS.
It exports event identity plus the LFPS-specific input context members Type,
Duration, DurationSec, DurationNS, PatternType, and StartsPattern through the
existing batched VSE -> COM -> Host path. The values remain raw numeric
observations; no LFPS type or pattern name mapping is inferred.

The execution record is in
scripts/m2-packet-extraction-3-results.md. It records 47,006 target events,
complete Host reconstruction, JSON read-back, and unchanged sacrificial trace
integrity. The three-slice product threshold is now met. Governance
retrospective eligibility still depends on the separately defined meaningful
interaction threshold; no retrospective is started by this product slice.

## M2-4 / DEMO-1 result

The combined extractor and PASS vs FAIL comparator are recorded in
docs/demo-1-pass-fail-results.md. Both candidate timelines were produced with
one shared extractor and complete Host reconstruction. The comparator found a
common sequence anchor and emitted candidate GUI windows without comparing
absolute timestamps or claiming root cause.

The FAIL working copy preserved input identity. The initial PASS working copy
grew by 20 bytes during VSE execution, including when restored from the
pristine Desktop zip. DEMO-I1 localized that mutation to 307 changed byte
positions across 15 ranges, including existing content and an appended
20-byte tail.

`DEMO-I2` then used the preserved pristine source artifact as an immutable
source, created a separate working copy, set the working copy read-only, and
ran the same combined extractor. The source SHA-256 remained unchanged, the
read-only working copy completed successfully, and the working copy also
remained unchanged for this run. DEMO-1 is therefore qualified for this
controlled source-preserving read-only mode. The earlier mutation remains a
known anomaly; the qualification does not claim that every trace, version, or
execution context is universally immutable.

## DEMO-2 one-click runner

`run-demo.ps1` packages the qualified Demo workflow behind one command. It
refuses to overwrite an existing output directory, records source SHA-256 and
size before and after, creates separate read-only sandbox copies, runs the
same combined extractor for both traces, and writes:

```text
pass-timeline.json
fail-timeline.json
comparison.json
source-integrity.json
report.md
sandbox/pass/<trace>.usb
sandbox/fail/<trace>.usb
logs/
```

The runner treats source evidence integrity as the hard safety gate. A missing
common anchor is reported in `comparison.json` and `report.md`; it is not
silently converted into a root-cause or PASS/FAIL claim.

`DEMO-2-WINPS-COMPAT` ran the exact repository-relative inputs in a fresh
Windows PowerShell 5.1 process. Add-Type, script parsing, existing-output
refusal, full extraction, comparison, and source-integrity acceptance all
passed. The Windows PowerShell comparator's higher resource cost remains an
observation for M5, not a correctness failure.

## DEMO-2 integrity closure

The runner now records SHA-256, size, UTC mtime, and read-only state for both
source traces and both disposable working copies. The run fails before
comparison when any source changes, either working copy changes, or either
working copy loses its read-only state. The Windows PowerShell 5.1
qualification harness asserts the same working-copy evidence in the emitted
`source-integrity.json`.

The controlled closure run is recorded in
`docs/demo-2-integrity-closure-results.md`. It passed on the known local
PASS/FAIL pair with source evidence integrity, working-copy integrity, and
the combined `analysis_input_integrity` all true. This closes the current
working-copy integrity hold for the selected source-preserving runner mode;
it does not claim universal immutability across traces, LeCroy versions,
Windows policies, or execution contexts.

## G0-C1 state authority correction

The natural fresh-session observation exposed a Lightweight consumer defect:
stale `memory/01_active_task.md` could steer task judgment toward an already
closed DEMO-1 hold even though the newer PLAN/evidence state qualified the
controlled source-preserving mode. The active-task file is a derived handoff,
not an independent authority.

The bounded C1 correction is recorded in the repo-local `AGENTS.md` rule and
the report-only `tools/test-state-authority.ps1` probe. On a conflict, the
consumer must emit `memory_state_conflict`, use current user instruction plus
verified evidence/PLAN for the product decision, and preserve the dirty memory
file for explicit reconciliation.

`FULL_VS_LIGHT_PILOT` is deferred. No Governance clone, runtime hook, writer,
validator, or framework file is added by C1. Product M3 resumes only after
this C1 rule passes the scoped fresh-session behavioral check and review.

The C1 result is recorded in
`docs/g0-c1-state-authority-results.md`. The script checks rule text only;
it does not prove Agent behavior. One separate fresh-context sub-agent case
passed on 2026-09-11; review and delivery are recorded with the scoped Git change. This controlled observation
does not establish universal natural-session recovery.

## 2026-10-13 — PCIe / USB source inventory and proposed slices

Research and slicing are complete locally. The source map and source register
record official PCI-SIG / USB-IF specifications, ECNs, test documents, installed
LeCroy manuals/constants/examples, and OS error-log references, with version,
access and reading-depth boundaries. They do not claim every document was
available or read in full.

- Source map: docs/pcie-usb-source-map-20261013.md
- Source register: docs/pcie-usb-source-register-20261013.json
- Proposed work: docs/pcie-usb-spec-slices-20261013.md (29 bounded slices)
- Documentation validation: artifacts/evidence/pcie-usb-research-20261013/validation.json

Current evidence distinguishes this dirty c100ee1 checkout from the clean
f417eec delivery checkout / remote main. W1-W5 observation timeline/report
work was already delivered via PRs #19-21; old B3-unstarted wording must not
cause that work to be repeated. This does not claim full B3 spec/policy or
root-cause evaluation. Local G3 and B2h work is not all present on main.

Existing bounded PASS results remain within their original scope. The first
proposed implementation is S01 input/applicability/selection contracts, followed
by USB U01 coverage and U02/U03/U05 fields/native transactions, or PCIe P01/P02
coverage/native grouping. G01 product policy and G02 vendor-register meaning
remain dependent on engineer definitions; those gates do not block unrelated
source-backed preparation. Restricted normative text and suitable captures are
separate prerequisites for the rule slices identified in the plan.

This session changes documentation only. It does not implement these slices,
run LeCroy/COM/VSE/GUI or hardware, contact engineers, submit access agreements,
commit, push, create a PR, or merge. Existing instruction/memory files and
unrelated dirty work are preserved. New report verdicts must respect the frozen
W1 typed contract; opaque extension text cannot create verified report facts.

## 2026-10-13 — S01 offline contract local checkpoint

Owner decision: APPROVE WITH CHANGES. Only S01 offline schema, validator,
fixtures, compatibility tests and trace-eligibility contract were authorized.
All other 28 slices remain candidates. U01/P01 require a separate execution
decision; LeCroy/COM/GUI/hardware, commit, push and merge were not authorized.

S01 is locally implemented without modifying either extraction/scoring pipeline:
- schemas/s01-input-manifest-v1.schema.json
- schemas/s01-trace-eligibility-v1.schema.json
- tools/s01_contract.py
- tests/s01/ (12 JSON fixtures, independent oracles and focused tests)
- docs/s01-offline-contract.md

The contract separates API support, field applicability and actual availability
from event observation and selection/retention/extraction coverage. Observed
absence requires a known bounded window and coverage prerequisites. Recorded
observations require a same-trace saved-output/manual-review/legacy reference;
applicable reviewed documentation can support API knowledge but not establish
runtime availability. Unknown, not applicable and unsupported remain distinct.

42 offline tests passed, including 64 handwritten readiness expectations.
Two existing saved JSON formats were read without following trace paths; their
bytes and original decoded content were preserved, with new coverage unknown.
Eligibility is input readiness only; qualification remains NOT_EVALUATED.
The focused review findings on document-only proof, source applicability and
non-finite JSON numbers were corrected and covered by regression cases.

Evidence: artifacts/evidence/s01-offline-contract-20261013/verification.json,
tests.txt and synthetic-eligibility.json. Synthetic fixtures do not qualify any
real trace or later slice. Legacy compatibility recognizes only the two explicit
formats documented in docs/s01-offline-contract.md and does not rerun their
historical validators. Existing PASS scope is unchanged.

W1-W5 frozen contract and the clean f417eec delivery checkout remain unchanged;
no untracked implementation was moved between checkouts. The roadmap now lists
an Engineer Question / Expected Observation for each of its 29 candidates.
Stop at this local S01 checkpoint. No automatic U01/P01 start, commit, push,
PR, merge, reset or runtime execution follows from this result.

## 2026-10-13 — S01 review and U01 offline preparation

Current owner instruction: review S01, then proceed to the next slice if no
blocking issues. S01 review found no P0/P1 blocker within the offline contract
scope; the 42 tests were rerun successfully. S01 code, schemas, fixtures and
historical evidence were not changed. Review: docs/s01-review-20261013.md.

Only U01 was started. The independent selection preparer, USB host, protected-copy
runner and saved-result assessor are ready locally, without editing the old
extraction/scoring pipelines or W1-W5. Seven modes cover packet default/CRC off/on,
transaction-all, and transfer default/complete/incomplete. Each index range is
level-local and post-dispatch; callback/sample counts remain separate.

13 Python tests and 6 managed callback cases passed, including C# compilation
and Windows PowerShell 5.1 syntax checks. The actual known USB input SHA-256 and
104136704-byte identity match the historical source record. A no-COM preflight
recorded current executable/manual/constants identities and prepared script
hashes. New output is isolated under artifacts/evidence/s01-review-u01-20261013.

Actual mode, coverage, bad-CRC and incomplete sample eligibility remain unknown;
S01 input matrix is partial and qualification NOT_EVALUATED. No runtime run has
occurred. Prior explicit LeCroy/COM/GUI exclusions are retained while a concrete
readonly-copy execution plan is presented for owner scope confirmation.
No hardware, P01/U02/other slice, commit/push/merge/reset or checkout transfer.
U01 scope and exact pending command: docs/u01-selection-coverage.md.
## 2026-10-13 — Owner-authorized serial slice workflow / runtime checkpoint

Owner explicitly authorized readonly U01 runtime and continued per-slice
implementation, validation and review without repeated confirmations. This
supersedes the earlier pending-runtime authority wording, not the evidence gates.
Hardware, commit/push/merge/reset and checkout transfer remain excluded.

U01: seven named selections completed twice with identical semantic output.
Review accepts bounded selection transport on the exact USB trace/software.
CRC-on adds10 whole-trace callbacks outside the0-200 window; not independently
qualified as bad-CRC examples. Incomplete transfer sample is empty/unknown.
Resolved unary-negative CSL template failure by v3 explicit NA wire token;
resolved activation-only RPC race with bounded retry before any trace opens.

U02: 128 SSP LINK_CMD rows repeat identically, LGOOD0-15/LCRD1A-D observed.
Two GetPacket raw64-bit packets match both word info/CRC5 fields by USB3.2
Figure7-13. No CRC correctness or other command/mode qualification is claimed.
U03: 128 LFPS rows repeat identically and all raw fields match the existing
same-SHA saved timeline; native labels retained, wake/reset success unevaluated.

U04: actual native single-packet export of3 saved LTSSM callback indices does
not expose a confirmed state-field label; blocked_field, no guessed in.State.
U05: bounded native TRA/XFER CSV discovery confirms separate group namespace
and G2 observations, but explicit child packet refs/payload/status qualification
remain absent. Full U05/P02 grouping stays HOLD on those prerequisites.

P01: six native PCIe selection profiles completed twice with identical output
and protected identities preserved. TLP704/DLLP2147145 exist but none are in
window0-200. Native SPLIT resolves to4, not the2 in one manual table. Display
filters/native effective range/capture scope/epoch remain unknown. Review accepts
bounded transport only. No existing extraction/scoring or W1-W5 changed.

Canonical checkpoints: docs/serial-slice-checkpoint-20261013.md,
docs/usb-field-probes-20261013.md, docs/pcie-selection-checkpoint-20261013.md.
Evidence: artifacts/evidence/serial-slices-20261013/verification.json and
per-slice review/run outputs. Other19 candidates retain individual prerequisites;
G01/G02 require engineer definitions. This is not all29 completion or certification.
Existing authority permits subsequent eligible work without routine reapproval.

## 2026-10-13 — Serial continuation P03 -> I01 -> I02 -> P11 -> P10

Owner authorized serial implementation/validation/review with no recurring approvals.
Five bounded checkpoints are locally complete, not all29 qualification.
P03: DLLP2147145/TLP704 callbacks;73/51 field samples;two runs equal;
18 representative packets agree via separate native ExportToText path (same decoder).
Missing/unknown mode, epoch, retention, bounds, error-positive and nonzero-scale
samples remain explicit; raw length/scale encoding is not normalized.
I01:124 P03 samples composed with frozen W1-W5 commit f417eecb; base model,
Markdown prefix and HTML outside added source block preserved.517 pointer links resolve.
I02:128 U02 samples composed with current C5 renderer; source replay and exact FAIL
trace binding, original C5 JSON/ranking/HTML preserved;128 packet pointers resolve.
P11:9 valid Recovery state points,2 invalid points retained,2 valid L0 points;
EQ/HotReset/physical-reset and continuous intervals remain UNKNOWN. Fresh same-SHA
B1b0 constant probe succeeded after absolute-path correction. Earlier failed
relative-path OpenFile attempt and owned cleanup retained; all native processes exited.
Change-only legacy extractor can omit validity-only changes; no timing/PHY/EQ verdict.
P10:LinkControl standard raw view adds CommonClockConfig/ClockPM using PCI-45 WDK
layout, source page updated2026-06-29. At query10360: merged/write values2,1,0;
all3 native CATC fields match, write request10354;readback unknown. Query3300 all3
unknown. Device role/RC/wire state/L1SS/CLKREQ electrical/effective/policy unqualified.
Dependencies located in current c100ee1b vs frozen f417eecb checkouts; no file transfer.

Validation:118 slice Python tests plus47 frozen W1-W5 tests plus14 existing B2h2
regressions,8 managed callbacks and2 activation recovery cases. Canonical verification
also proves972 existing files unchanged,2 planned docs updated, and append-only
PLAN/closeout prefixes; both heads and source traces unchanged, delivery remains clean.
Evidence:artifacts/evidence/p03-serial-20261013/verification.json and five review files.
Docs:p03-field-checkpoint-20261013.md, i01-i02-report-checkpoint-20261013.md,
p10-p11-observation-checkpoint-20261013.md; serial checkpoint and roadmap refreshed.

Remaining14 candidates retain individual prerequisites: P04/P05 normative text and
continuous same-epoch capture, P06 group membership/request identity, P07/P08
applicable AER/DPC field inputs (saved extended chain stops at unobserved0x200,
not proof of absence), P09 both adapters, U06 further command/response scope,
U07-10 native group/payload/status evidence, U11 USB2 input, O01/O02 saved host logs.
U04/U05/P02 retain data gates;G01/G02 still require engineer definitions.
No existing PASS expanded; W1 opaque verdict untouched. No hardware/capture,
engineer contact, commit/push/PR/merge/reset, or movement of untracked work.
Authority continues for eligible followups; no routine permission question.


## 2026-10-13 — Owner-authorized slice source push

Owner said "先push上去": necessary commit/push authorized for the reviewed slice
sources/fixtures/small evidence on codex/pcie-d1e-f0-baseline. Existing5 local
commits are included in this branch's publication; no merge/rebase/reset.
Raw captures, local working copies, giant C4 timeline JSON and unrelated
untracked work stay local. Required current-checkout B2 dependencies are staged
in place; differences vs origin/main recorded, no copying across checkouts.
Delivery scope and fresh-clone replay limitations: docs/slice-push-checkpoint-20261013.md.
Canonical delivery record: artifacts/evidence/slice-push-20261013/delivery.json.
This publishes bounded prototypes and historical local evidence; not all29 or
full protocol qualification. Prior checkout/head/trace preservation results remain
historical evidence; push state is a separate gate.

## 2026-10-16 — GL3525 Billboard Chapter 9 new trace first-pass analysis

New owner-provided input: Desktop/1016/GL3525-OVY1L_Billboarda-CV_test_issue,
9 distinct .usb captures (6 FAIL / 3 PASS), 235,976,744 bytes. Owner confirmed
filename labels; same firmware/procedure and exact CV subtests remain unverified.
This is a new dataset and does not reopen the historical USB3 or PCIe milestones.

Local first-pass complete: all 9 protected copies opened and native transfer CSV
exported. Existing U01 probe ran 7 selections each on PASS_01 / FAIL_01, all 14
transport assessments consistent. Native packet counts and transfer row counts
match U01 default callbacks on that pair; incomplete counts 0 / 1 match native
Cplt=NO rows. Old USB3 DEMO ran normally on PASS_01 but extracted zero selected
events, so its pair wrapper stopped before FAIL_01 and no C5 ranking was run.

All 6 FAIL traces have existing descriptor-request annotations. FAIL_01 transfer
1386 at 35.611541400 sec is native Cplt=NO with Not Enough Data=0 bytes; FAIL_06
also has an incomplete configuration request. PASS_04 shares a data-shortage
flag on configuration index 1 with FAIL_02-06, so this flag alone is not a
failure criterion. No firmware cause, compliance verdict, device identity,
complete capture coverage, or setup/data/status grouping qualification claimed.

Report: docs/gl3525-billboard-ch9-first-pass-20261016.md.
Full local evidence: C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard/.
All nine source and working-copy identities unchanged; native processes exited.
Next bounded diagnostic candidate: obtain setup/data/status and native packet
references at the annotated transfers. This supplies new input for the USB2 /
EP0 work; it is not U09/U11 adapter qualification. No product implementation,
canonical memory write, staging, commit, push, PR, merge or hardware operation.
## 2026-10-16 — TRIAGE-1 single-trace guidance / Automation-first A-B

Owner clarified the product target: one trace, no supplied failure time or PASS
baseline, up to three suspicious episodes with position, observation, reason and
conditional engineer action. Root-cause proof is not a prerequisite. Subsequent
owner research prioritizes native Automation reuse, minimal VSE only for proven
field gaps, and no large viewer or additional packet-class expansion.

Local prototype implemented: tools/run-usb-control-triage.ps1 supports Automation
and Vse backends. API-only level-3 CSV and minimal USB2 control VSE observations
feed the same discover/render functions. Labels, Markers and known failure times
are not discovery inputs. Blank CSV fields remain unknown. Native SETUP-prefixed
payload is byte-checked before deriving response data; capped prefixes are not
zero-filled. Existing C5 pipeline/renderer and U01 COM host remain unchanged.
Default remains explicit Vse (no silent fallback), pending further API composition
work; both backends are selectable and their present evidence limits are visible.

Validation: 31 new tests plus 14 existing U01 tests passed; 9 traces yielded
23,456 native control records cross-checked to saved CSV indices/times/address/EP.
Repeated FAIL_01 normalized native records matched exactly. On current known-data
replay, A has annotated locations in Top3 on 2/6 FAIL files, B on 6/6; annotation
point coverage is 2/9 vs 8/9. Both produced zero episodes on three PASS files.
FAIL_06 transfer296 is outside B Top3. Source traces and protected copies remain
unchanged. Browser checks cover primary/secondary cards, empty state, copying and
390px layout. One favicon404 is separate from script execution.

Native10.40 probes: 14 AnalyzerErrors counts are zero on FAIL_01 despite its
incomplete control request. GotoTime/GotoUnit returned (visual landing unverified).
ExportVisibleTraList works but this profile emits894015 index/level/name-only
objects (82,027,165 bytes); no timestamps/request/payload. Bounded native transfer
data export returns18 descriptor bytes. Thus A's tested projection is incomplete,
not proof all possible Automation-only compositions are insufficient. One ordered
live sample measured A14707ms/B9770ms, not a controlled performance comparison.

Qualification boundary: v2 missed reserved FAIL_05; that miss is preserved. After
inspection it became regression input for a header/larger-followup relationship,
so it is not held-out validation. PASS_02 remains unused for rule tuning. Engineer
usefulness/time savings and an unseen FAIL qualification remain NOT_TESTED.
No USB-CV compliance, root cause, full capture coverage, packet membership or
cross-reset physical identity claim. Local implementation is complete within
this scope; product acceptance is pending those separate observations.

Docs: docs/usb-control-triage.md; docs/usb-control-single-trace-contract.md;
docs/lecroy-1040-triage-capabilities.md. Canonical local evidence and report index:
C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-single/.
Next: engineer follows one report and a new FAIL trace is evaluated; first assess
native API gap-filling rather than expand VSE or duplicate LeCroy views. No memory
record write, commit, push, PR, merge, hardware operation or source capture save.
## 2026-10-16 — TRIAGE-1 tool plan / owner priority

Current owner priority: define a usable tool plan and implementation slices before
more report-only polishing or new analysis rules. Product posture remains
Prototype PASS / Product Validation Pending. Plan: docs/usb-control-tool-plan.md.

Baseline preserved: 11 source/test/contract files snapshotted with hashes,
rule usb2-control-guidance-3, output usb-control-inspection/v1. All 18 detailed
HTML reports plus their models and original index are bundled for offline review;
the37 original release files are byte-identical. Package has39 verified local
references and no external page dependencies. No algorithm/ranking changes.

New native evidence: GotoUnit(3,index) visibly lands on FAIL_01 transfer1386
(35.611541400,13/0), FAIL_06 transfer562 (40.351786032,19/0),372
(27.608155682,5/0),446 (33.191925582,12/0). Actual Transfer view fields match.
Native UI also returned from446 to372 using the Go-to dialog. This updates the
earlier GUI-unverified checkpoint only for these observed positions; it does not
qualify every transfer, GUI read-back, full handshakes or root cause. HTML has no
API bridge yet. Clipboard-to-native paste and real engineer use remain untested.

Implementation slices (not started): TOOL-01 browser button/local COM navigation;
TOOL-02 select-one-trace/run/report/navigate integrated entry; TOOL-03 UI identity,
candidate totals and recovery states; TOOL-04 unpack-and-start trial package;
TOOL-05 unseen cases and engineer task/time validation. TOOL-01 is next. Existing
VSE/Automation acquisition and discovery are reused, no new ranking rules.

Review notes: docs/usb-control-product-validation.md. Minor UI gaps include trace
identity hidden in details, missing index orientation, omitted candidate count
buried in limitations, and absent native navigation instructions. Frozen reports
remain unchanged; these fixes belong to TOOL-03. No new unseen traces or human
timing were obtained. Local evidence and portable ZIP remain under:
C:/Users/reiko/.codex/visualizations/2026/10/16/01a14297-966e-7b51-b3e6-572fecb51b9e/gl3525-billboard-validation/.

This session delivers planning/validation artifacts, not an implemented desktop
tool, one-click bridge or release. No commit/push/PR/merge, hardware action,
source-capture save or global-memory edit. Prior dirty work retained.

## 2026-10-16 — Tool plan review incorporated (r2, documentation only)

Owner-supplied review explicitly limits this round to plan/acceptance revisions;
TOOL-01 implementation is not authorized by this revision. Current plan:
docs/usb-control-tool-plan.md (r2). Existing prototype remains Prototype PASS /
Product Validation Pending; no new runtime, coexistence or usability result.

Revised order: TOOL-01 -> TOOL-02 -> TOOL-02.5 -> TOOL-03 -> TOOL-04 -> TOOL-05.
TOOL-01 first investigates safe coexistence with an already-open LeCroy using
controlled sessions and verified ownership; existing all-process guard stays
until isolation is proved. Includes STA message pump, serialized operations,
out-of-worker timeout observation, late-reply protection, owned-only cleanup,
HTTP/API/visually-confirmed positioning separation, and exact Host/Origin plus
session-token/candidate authorization and non-shell-interpolated parameters.
TOOL-02 adds actual native Windows drag-and-drop and file selection, transfers
paths over IPC instead of uploading full traces through the browser, and keeps
the required readonly-copy protection. Minimum candidate total/omitted count
and explicit USB2 EP0/not-USB-PASS scope are required before early trials.
TOOL-02.5 observes1-2 engineers on familiar cases before TOOL-03 UI improvements;
this is usability evidence, not unseen-case validation. No engineer contacted.
TOOL-04 separates new-unpack-directory from clean-Windows-environment evidence
and records large-trace timing, memory and temporary-disk usage. TOOL-05 retains
unseen FAIL/PASS and full-task cost, including coexistence/recovery overhead,
useful candidates, actual misleading directions and undecided annotations.

No source code/rule/contract changes, COM/UI execution, hardware action,
commit/push/PR/merge or memory write. Original plan flow and five main slices
are preserved with the added early human-validation checkpoint. Next planned
work remains TOOL-01, not started. Review requirements are mapped in the plan.

## 2026-10-16 — Authorized TOOL implementation and native UI correction

The owner approved r2 and authorized implementation in slice order. This
supersedes the preceding documentation-only work order. Implementation and
current acceptance boundaries are in docs/usb-control-tool-results.md; usage
and official UI references are in docs/usb-control-tool.md.

TOOL-01: implemented the asynchronous controller, private candidate binding,
pumped STA worker, integrity checks and owned-only restricted navigation.
Actual report-button and native-workspace landings match FAIL_01 1386 and
FAIL_06 562/372/446; repeated navigation reuses OpenFile. Existing native
work is refused before takeover. Safe multi-instance coexistence is not proved,
foreground switching can be refused by Windows, and actual permanently hung
COM recovery remains unqualified.

TOOL-02: implemented native file selection/FileDrop IPC and frozen VSE analysis.
Actual native picker -> analysis -> candidate workspace -> LeCroy is verified;
physical Explorer drag qualification is pending because the Computer Use drag
API refused a cross-window endpoint. Source/read-only-copy checks passed.

TOOL-02.5: the user personally tried the initial tool and reported poor UI and
unexpected external web pages. This is real negative feedback, not a PASS.
Following the user's instruction to research similar tools first, checked
official Saleae Logic 2, Wireshark, Total Phase and Windows guidance, then
implemented the native inspection workspace. TOOL-03 objective fixes include
candidate/detail synchronization, first-screen location and next-step hints,
native context/source tabs, scoped empty results and optional HTML export;
normal use no longer launches an external browser. New UI needs human retest.

TOOL-04: explicit 13-source-file trial ZIP with manifest and verified CRC/bytes;
unpacked to a fresh directory and launched from another cwd. PASS_04 analysis
and scoped empty state verified there. Largest current-batch trace (FAIL_06,
about 54 MB) analysis/resources recorded; this is not a general large-trace or
clean-Windows qualification. TOOL-05 unseen-case and complete engineer-time
acceptance remains pending actual participants/data. No ranking rules added.

Validation: 15 controller/native-IPC boundary tests, 31 frozen USB-control tests
and 14 U01 tests passed. All 11 frozen source/test/contract files, nine original
traces, bound copy identities, package bytes and earlier dirty text prefixes
verified. Source snapshots and test/GUI evidence remain outside Git under
the tool-implementation directory alongside the prior validation directory.
Local trial implementation is delivered; not all slice acceptance gates are
passed. No commit, push, PR, merge, hardware writes or global-memory edits.

## 2026-10-16 — TOOL-03 approved palette and portable startup repair

Owner approved the existing layout with neutral light semantic colours and
state-dependent primary actions. Implemented native colour tokens, explicit
button interaction/focus states, neutral candidates with blue selection,
tab selection underline, import wording and operation-error recovery state.
No multi-theme feature or new analysis rules. Human usability/time saving
remains pending; subjective appearance scores are not acceptance evidence.

Owner reported silent startup on another engineer's LeCroy 10.50 machine and
requested default installation detection before custom selection and bundled
Python. Added a precompiled native startup window and persistent logs; portable
ZIP contains the hash-checked official Python 3.13.16 x64 runtime and license.
Default LeCroy paths and both COM registry views are checked; only absent paths
prompt for selection. No system execution-policy or COM-registration writes.
10.50's documented ProgID is unchanged, but remote runtime remains unverified.

During the new package trial, actual FAIL_06 and FAIL_03 imports exposed a
local regression: new AppData paths were still virtual when passed to the
out-of-process LeCroy COM server. Fixed by resolving the physical directory
after creation, in controller and startup paths. Reproduced the old/new path
difference and retained failure logs. Bundled-runtime actual reruns in AppData
now return FAIL_01 1386, FAIL_06 562/372/446, PASS_04 no candidate, source hashes
unchanged. Remote silent startup is not attributed to this local defect.

Validation: controller/distribution suite18, frozen USB suite31, U01 suite14;
native startup harness12 assertions; official runtime SHA-256, package CRC and
exact files; native startup from another cwd with empty PATH. No clean-Windows,
remote 10.50, engineer-time or general coexistence qualification. Engine,
ranking, VSE, adapter and COM navigation sources remain unchanged; runner only
accepts the detected executable path for metadata. Details/evidence are in
docs/usb-control-tool-results.md and the external tool03-portability directory.
Local implementation/package work; no commit, push, merge or global-memory edit.

## 2026-10-16 — Owner-authorized USB tool source delivery

Owner explicitly requested push after the portable-r3 repair. This authorizes
the source/documentation commits and push to the existing
codex/pcie-d1e-f0-baseline branch, superseding the prior no-commit/push work scope.
The selected bundle contains31 USB-tool source/test/documentation paths plus
the separately committed session closeout. Proprietary captures, generated
timelines, portable binaries/runtime ZIP and unrelated PCIe work remain local.
Current tests18+31+14 pass. Source delivery does not establish remote10.50,
clean-Windows or engineer/time-saving acceptance; no PR or merge requested.
The exact remote-head and preservation result is recorded in the external
push-20261016 evidence directory after the push operation.
