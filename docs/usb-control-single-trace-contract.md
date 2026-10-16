# Single-trace USB2 control-transfer guidance v1

Owner target (2026-10-16): one `.usb` trace -> up to three ordered inspection
episodes -> position, observed behavior, inspection reason and conditional next
step. A PASS trace, filename label, marker, known failure timestamp and root-cause
proof are not prerequisites. Absence of a candidate is not a USB PASS verdict.

## Evidence and scope

USB2 native control-transfer context only. The installed LeCroy VSE manual
§5.2.4 (PDF 89) documents Completed, Halted, request fields and payload length.
Installed VSTools.inc ReportXferEventInfo/ShowPayload supplies field and bounded
payload access examples. Transfer index is a native **transfer** index, never a
packet number. Channel/address do not establish device identity across resets.
The adapter does not reconstruct child packet membership or infer SETUP ACK,
individual handshakes, or status-stage completion from missing data.

Microsoft's [control-transfer explanation](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-control-transfer)
supports separating request/data/status and inspecting the corresponding native
traffic. The [USB-IF specification source](https://www.usb.org/document-library/usb-20-specification)
is the normative reference for future compliance work, not a claim that this
heuristic implements Chapter 9 compliance. A supplied networking flow-control
page is not used as USB evidence.

The actual first native replay shows transfer payload includes the 8-byte SETUP
prefix (a requested 18-byte device descriptor has native payload length 26).
The adapter checks all eight bytes against independently serialized request
fields before deriving the remaining data length or descriptor prefix. If that
check fails, data-stage length remains unknown. It never treats native payload
length 8 as eight response bytes. Individual packet handshakes remain unknown.

The extractor traverses all native transfer callbacks, emits only USB2 control
records (maximum 100,000), and retains at most 64 actual payload bytes per record.
It exports no filename-derived classification or trace marker. Completion and
payload are decoder observations. Prefix truncation is explicit; missing bytes
are never zero-filled. Exact seconds/nanoseconds are preserved as integers.

## Discovery policy and boundaries

Rules are inspection heuristics, not fault verdicts or calibrated probabilities.
An incomplete transfer is a candidate, with capture-tail caution where applicable.
A halted/error transfer needs corroborating request history to receive priority;
isolated halted requests remain unranked observations because negative tests may
exercise them intentionally. A short transfer alone is not a candidate.

Development trace FAIL_02 demonstrated that native Completed can equal 1 even
with only the verified SETUP payload and a long native duration. Rule revision 2
therefore also requires both zero response data and duration >10 times the local
P95 of at least five prior successful data-bearing descriptor reads at the same
channel/speed/address/endpoint (within 256 records and 10 seconds, bounded by the
observed assignment/deconfiguration breaks below). This is a relative inspection
heuristic, not a specification timeout. Explicit halted negative requests are
excluded from this rule. Revision 1 and its nine outputs are preserved locally;
revision 2 is frozen again before marked-outcome evaluation. No held-out raw
event was inspected to construct this revision; fully unseen qualification is
still not claimed because earlier annotated reports were available.

Revision 2's held-out replay missed FAIL_05 despite its existing BOS annotation.
Post-evaluation inspection showed a valid five-byte BOS header followed by a
larger read with no data; the preceding successful read was itself slow, so a
relative-duration rule was insufficient. Revision 3 adds the independent
header-declared-length / empty-larger-followup relation for configuration,
other-speed configuration and BOS. It requires a matching actual header and
request identity, not a marker or an assumed mandatory descriptor. FAIL_05 is
thereafter a regression sample, **no longer held out**. PASS_02 remains unused
for rule tuning. Revision 2's miss is retained in evaluation-v2.json; a new
unseen FAIL capture and engineer usefulness validation remain outstanding.

Request comparisons require the same native channel, speed, address, endpoint,
direction, request type/recipient, bRequest, wValue and wIndex; exact retry
comparisons additionally require equal wLength. Nearest prior successfully
completed, non-halted data-bearing response can support a change-of-response
observation. No comparison crosses an observed SET_ADDRESS at the same address,
SET_CONFIGURATION(0), or a bounded-context gap. Unobserved physical resets remain
a limitation, so the output never calls repeats the same physical operation.

Related neighboring candidates are combined into one inspection episode. The
first candidate, subsequent progression and local context are retained. Ranking
uses evidence strength and stable chronological tie-breaking, not labels. The
Declared descriptor length checks also require verified response bytes. A normal
8-byte header probe of an 18-byte device descriptor, or a complete short string
whose bLength equals its response length, is not a candidate. Configuration and
BOS wTotalLength use their documented header fields; missing prefix bytes remain
unknown. Source: [Configuration descriptor](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbspec/ns-usbspec-_usb_configuration_descriptor).
This is structural inspection, not a complete USB-CV test implementation.

HTML shows one primary episode and at most two secondary episodes; internal
priority numbers and raw JSON are secondary evidence.

## Verification plan (before implementation)

- Hand-authored invariant fixtures: empty/healthy, incomplete, data/no-data,
  earlier-success then halt, unsupported negative request, legitimate short
  response, repeated requests, capture tail, boundary/gap, malformed fields,
  payload truncation and mismatched transfer identity.
- Mutation tests: changing filenames, markers and known timestamps must not alter
  analysis; editing event fields must alter the result or be rejected. No marker
  enters the normalized event model.
- Renderer checks: four required card fields, exact timestamps, explicit transfer
  namespace, no fake packet refs, HTML escaping, offline resources, no-candidate
  state and copyable positions.
- Actual protected-copy extraction: compare native transfer indices/times and
  request labels with the earlier CSV, and repeat one trace for deterministic
  event equality. Preserve source/copy hashes, sizes, mtimes and read-only state.
- Freeze rule source hash before marked-outcome evaluation. Reserve FAIL_05 and
  PASS_02 from rule-tuning fixtures. The analyst already saw the prior first-pass
  report: this is held-out replay, not a claim of fully unseen independent data.
  Only the evaluator reads markers after discovery has finished. Report Top-3
  location coverage and unmatched candidates, never infer false positives from
  missing annotations alone. Engineer usefulness/time savings remain human tests.

Historical C5 PASS/FAIL scoring and renderer remain intact. A sibling report
adapter reuses the offline engineer-first presentation pattern; it does not feed
single-trace data into a paired C5 schema.

## Owner steering: Automation-first evidence comparison

The owner subsequently requested an A/B check before further VSE expansion.
`-Backend Automation` acquires native level-3 CSV and AnalyzerErrors without
creating a VSE engine. Its adapter supplies the same discovery/render functions;
blank completion/status/data/request fields stay unknown. Native semantic names
classify known standard requests; raw bmRequestType is not falsely reconstructed.
`-Backend Vse` supplies the bounded context fields already validated above.

The default remains explicit Vse, with no silent fallback. Tested A projection
limitations do not prove an Automation-only solution impossible. In particular,
the local ExportVisibleTraList call works but returned only index/level/name in
this profile; a bounded ExportUSBTransferData call retrieved descriptor bytes.
Further work should first evaluate native API combinations for proven gaps,
while preserving the minimal VSE path and current report scope. Full current
evidence and acceptance boundaries are in usb-control-triage.md.
