# DEMO-C5 Automatic Suspicious-Region Discovery

## Objective

Find suspicious FAIL regions without receiving an engineer-supplied timestamp,
event index, or root-cause hint. The engineer-labeled failure interval is used
only after the run as a qualification answer, never as an algorithm input.

## Method

The tool builds a PASS behavioral baseline from relative 10 ms sliding windows
with a 1 ms stride. It scans the FAIL timeline with the same windowing and
ranks non-overlapping candidates using:

- LFPS event burst count and LFPS share of the window;
- raw LFPS signature rarity relative to the PASS trace;
- LTSSM event density; and
- LINK_CMD activity deficit relative to the PASS baseline.

Raw LFPS signatures contain only the observed numeric values:
`LfpsType`, `PatternType`, `DurationNs`, and `StartsPattern`. No enum name is
inferred.

The algorithm does not align PASS and FAIL by absolute timestamps. Each trace
is windowed relative to its own first observed event. The output is a triage
ranking, not a root-cause or PASS/FAIL verdict.

## Qualification command

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\discover-c5-suspicious-regions.ps1 `
  -PassTimelinePath <pass-timeline-with-timestamp-ns.json> `
  -FailTimelinePath <fail-timeline-with-timestamp-ns.json> `
  -OutputPath <c5-output>\suspicious-regions.json `
  -TopK 3
```

The known engineer-labeled interval is consulted only after this command
finishes. Qualification asks whether that interval intersects one of the Top
3 candidates; it is not passed to the script.

## Known-pair result

The C5 run used only the PASS and FAIL timeline JSON files as input. The
engineer-labeled interval was checked after the artifact was written:

```text
Top 1 candidate: 21.786067664--21.796067664 sec
Top 1 score:     0.849435
Top 2 candidate: 13.996067664--14.006067664 sec
Top 2 score:     0.846479
Top 3 candidate: 21.796067664--21.806067664 sec
Top 3 score:     0.812368
```

The expert-labeled interval was `21.789454560--21.801473168 sec`. It
intersects Top 1 and Top 3, and therefore the known-pair Top-3 qualification
passed. The tool never received this interval as an input.

Top 1 contained 3,042 LFPS events, 5 LTSSM events, no LINK_CMD events, and
821 LFPS events whose raw signatures were rare relative to the PASS global
baseline. The raw signature values remain numeric; no LFPS enum name was
inferred.

The generated canonical artifact is:

`c5-output-20260911-v3/suspicious-regions.json`

## DEMO-V1 offline HTML report

The C5 JSON is now rendered by `tools/render-c5-html.ps1` into a single
offline HTML report. The renderer is presentation-only: it does not change
the C5 scoring or accept an engineer-labeled timestamp as input. It shows the
Top 3 candidates, exact nanosecond timestamps, scores, observed reasons,
raw LFPS fields, PASS/FAIL event-count overview, source-integrity status, and
the claim boundary. The JSON remains the canonical analysis artifact.

The verified local report is a Traditional Chinese (`zh-Hant`) interface with
technical terms retained in English where useful:

`c5-output-20260911-v9/report.html`

The WinPS 5.1 read-back checks confirmed the report contains the Top-1 time,
Chinese labels with English technical terms, claim-boundary section, PASS/FAIL
overview, integrity section, and no script or network dependency.

## DEMO-V2 engineer-first triage report

The presentation layer was revised without changing the C5 JSON or scoring:

- adjacent or overlapping C5 windows are grouped into a suspicious episode;
- the primary episode and exact GUI inspection interval are placed first;
- `Triage score` is explicitly ranking metadata, not confidence;
- FAIL-region values are compared with the PASS p95 window baseline;
- misleading cross-signal bar charts are removed;
- raw LFPS fields, PASS/FAIL totals, integrity, and claim boundary are
  collapsed into details.

For the known pair, windows `#1` and `#3` are grouped into one episode:

```text
21.786067664 -- 21.806067664 sec
LFPS       5,377
LTSSM          6
LINK_CMD       0
```

The verified DEMO-V2 report is:

`c5-output-20260911-v10/report.html`

The local timeline is intentionally an interval and episode summary. It does
not fabricate per-event positions that are not present in the C5 artifact;
packet-level confirmation still belongs in the LeCroy GUI.

## DEMO-V3 evidence timeline

DEMO-V3 keeps the DEMO-V2 information hierarchy and adds actual event
positions from the referenced `fail-timeline.json` artifact. For the primary
episode, the renderer found 5,383 events, including 6 LTSSM markers. The
markers include the observed positions `21.789454560 sec` and
`21.801473168 sec`; LFPS is rendered as density across the interval and
LINK_CMD is explicitly shown as absent.

The report also shows the PASS and FAIL trace basenames on the first screen.
Exact nanoseconds, C5 window IDs, scores, and artifact paths remain in the
analysis-details section. If the referenced timeline is unavailable, the
renderer emits a clear fallback message instead of fabricating event
positions.

The verified DEMO-V3 report is:

`c5-output-20260911-v12/report.html`

## DEMO-V4 plain-language triage summary

DEMO-V4 is a presentation-only refinement over the same C5 JSON and DEMO-V3
event-position timeline. The Hero now states the observed local behavior in
conservative engineering language: the interval is almost entirely LFPS
activity, includes multiple LTSSM transitions, and has no observed LINK_CMD
activity. It does not infer a failed negotiation or a root cause.

The evidence timeline labels three selected actual LTSSM timestamps, including
`21.789454560 sec` and `21.801473168 sec`. Secondary candidate scores are
available only after expanding their details and are explicitly described as
ranking evidence rather than confidence. The raw LFPS section advertises the
observed `2200 ns` signature, and local PASS-baseline deltas use directional
arrows for faster scanning.

The verified DEMO-V4 report is:

`c5-output-20260911-v14/report.html`

This is the stopping point for the current UI-polish slice. The next product
slice is blind validation on an independent PASS/FAIL trace pair; no C5
scoring change is justified by this presentation work.

## DEMO-V5 instrument color semantics

DEMO-V5 keeps the DEMO-V4 layout and applies only semantic color changes for
an instrument-style engineering console. Graphite surfaces provide the base;
blue identifies information and LFPS activity; amber identifies triage
candidates, recommended actions, and LTSSM markers; muted gray-blue identifies
LINK_CMD; and green is reserved for qualified source integrity. No color is
used to imply a root cause or a confirmed failure.

The verified DEMO-V5 report is:

`c5-output-20260911-v15/report.html`

This completes the current presentation polish. The next product slice remains
blind validation on an independent PASS/FAIL pair.

## DEMO-V6 plain-language report copy

DEMO-V6 keeps the DEMO-V5 layout and semantic colors, then changes the visible
copy to follow an engineer's first-read workflow. The first screen now states
the most useful location, describes the observed behavior in plain Traditional
Chinese, and gives the LeCroy GUI action. Protocol names remain in parentheses
or in the timeline labels, while p95, ranking data, and technical limits stay
in expandable analysis details.

The comparison table now uses labels such as "問題區段" and "正常紀錄參考值"
instead of exposing `baseline` and `p95` in the main reading path. The timeline
explains what denser blue marks and amber LTSSM dots mean. The report still does
not infer root cause or product PASS/FAIL.

The verified DEMO-V6 report is:

`c5-output-20260911-v18/report.html`

This completes the current presentation work. The next product slice remains
blind validation on an independent PASS/FAIL pair.

## DEMO-V7 capability, method, and limitation copy

DEMO-V7 is a deterministic presentation-only refinement over DEMO-V6. It
separates the bottom section into three plain-language groups: what the tool
can do, how the comparison works, and what the tool cannot currently claim.
The Hero now says directly that the interval contains mostly LFPS activity,
six LTSSM changes, and no observed LINK_CMD activity. The secondary
candidate's ranking score remains available only inside technical details.

The report is generated from the existing C5 JSON. It does not use AI, change
the C5 scoring formula, or accept the engineer-labeled failure timestamp as
analysis input.

The verified DEMO-V7 report is:

`c5-output-20260911-v20/report.html`

This completes the current presentation-layer work. The next product slice
remains blind validation on an independent PASS/FAIL pair.

## Claim boundary

`candidates` are ranked inspection suggestions. They do not prove first
divergence, root cause, severity, or automatic PASS/FAIL classification. A
future slice may compare a selected FAIL candidate with a locally identified
PASS phase, but global semantic alignment is not required for C5.
