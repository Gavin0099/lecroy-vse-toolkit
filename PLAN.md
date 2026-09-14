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
| PCIe-G10 | Signal Expansion | CONDITIONAL; LTSSM/DLLP or other signals only when G3/G9 evidence shows TLP-only rules are insufficient. |
| PCIe-A1 | COM Automation Qualification | OPTIONAL / NOT STARTED; only if GUI focus seriously slows G1/G2, batch traces are needed, or G9 needs unattended runs. Scope limited to `OpenFile`, `RunVerificationScript` and their success/failure status; not coupled to extraction logic. |

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
