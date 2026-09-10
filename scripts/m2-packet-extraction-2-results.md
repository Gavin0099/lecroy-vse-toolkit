# M2-PACKET-EXTRACTION-2: USB3 LTSSM state event extraction

## Scope

- Input: the same real trace on a sacrificial copy.
- Target event: installed LeCroy decoded _USB3_LTSSM_STATE.
- VSE script: scripts/m2-packet-extraction-2.vse.
- Host harness: tools/run-m2-ltssm-extraction.ps1.
- Output: host-owned ltssm-batched-5.json outside the repository.
- Exported fields: event index, timestamp text from TimeToText(in.Time), and
  event type from GetEventName().
- Not exported: decoded LTSSM state name. No reliable 10.40 field name was
  established, so no state mapping is inferred.
- Excluded: severity, suspicious, root cause, GUI recommendation, comparison,
  and AI explanation.

## Delivery configuration

The installed 10.40 VSE files did not expose SendTraceEventOnly(). An initial
attempt using SendTraceEvent(_USB3_LTSSM_STATE) returned 0x80040200 before
event callbacks. The final run reused the M2-PACKET-EXTRACTION-1 delivery
configuration and filtered in ProcessEvent() by _USB3_LTSSM_STATE. This keeps
the event-delivery configuration evidence-based for this installation.

The first failed host attempt used a different COM event-interface GUID and
returned 0x80040200 with zero callbacks. Reusing the already validated M2-1
GUID fixed the host connection-point wiring. This was a harness defect, not an
LTSSM extraction result.

## Acceptance

| Check | Evidence | Outcome |
| --- | --- | --- |
| Real trace used | Fresh sacrificial copy of dp1 hub detect SSD fail-2.usb | YES |
| Existing M2 delivery configuration reused | Same channel, level, and trace-event selection | YES |
| VSE completes | RunResult=2, FinishedResult=2 | YES |
| Runtime | 6,413 ms | OBSERVED |
| Host notifications | 2 total: 1 event batch plus 1 summary | YES |
| Target events declared by VSE | 30 | YES |
| Target events reconstructed by Host | 30 | YES |
| Event index exported | First 8; last 3,092,354 | YES |
| Timestamp exported | First 67.664 us; last 21.801 sec | YES |
| Event type exported | All records _USB3_LTSSM_STATE | YES |
| JSON exists and is valid | Host write plus ConvertFrom-Json read-back | YES |
| Read-back match | Count and event records matched | YES |
| Event fields valid | Index, timestamp, and type present for every record | YES |
| Trace integrity | SHA-256, size, and UTC mtime unchanged | YES |

## Trace integrity

Before SHA-256: F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
After SHA-256:  F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F

Before size: 103062189
After size:  103062189

Before mtime UTC: 2026-09-10T07:01:12.5609905Z
After mtime UTC:  2026-09-10T07:01:12.5609905Z

## Verdict

M2-PACKET-EXTRACTION-2 PASS for the bounded _USB3_LTSSM_STATE extraction
slice using the existing batched Host delivery path.

This proves that the selected decoded LTSSM event can cross the existing
VSE-to-COM-to-Host path with index, timestamp, and event type preserved in a
verifiable JSON artifact. It does not prove that the decoded LTSSM state name
is available through the current 10.40 field API, and it does not prove
complete USB3 link-state decoding, triage, comparison, or AI diagnosis.
