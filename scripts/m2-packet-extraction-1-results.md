# M2-PACKET-EXTRACTION-1 execution record

## Scope

- Input: the known real trace on a fresh sacrificial copy.
- Target event: LeCroy decoded _USB3_LINK_CMD on _USB3_TX and _USB3_RX.
- VSE script: scripts/m2-packet-extraction-1.vse.
- Host harness: tools/run-m2-packet-extraction.ps1.
- Output: host-owned packets-batched.json outside the repository.
- Exported fields: event index, timestamp text from TimeToText(in.Time), and
  decoded event type from GetEventName().
- Excluded: severity, suspicious, root cause, GUI recommendation, comparison,
  and AI explanation.

The target is a protocol event exposed by the installed LeCroy VSE samples and
is not reconstructed by this repository.

## Transport isolation

The first implementation sent one NotifyClient() callback per matching event.
It completed traversal but did not preserve all records at the Host:

| Measurement | Result |
| --- | ---: |
| VSE declared _USB3_LINK_CMD events | 166,196 |
| Host event records received | 19,190 |
| Summary notifications | 1 |
| Result | NOT ACCEPTED |

This isolated a transport-framing problem in the per-event notification
approach. It is retained as negative evidence; it is not treated as a VSE
decoder count failure.

The implementation was then changed to send batches of up to 250 delimited
records per notification. The Host parses each batch and reconstructs the
individual event objects.

## Batched acceptance

| Check | Evidence | Outcome |
| --- | --- | --- |
| Real trace used | Fresh sacrificial copy of dp1 hub detect SSD fail-2.usb | YES |
| Existing M1 delivery configuration reused | Same channel, level, and trace-event selection | YES |
| VSE completes | RunResult=2, FinishedResult=2 | YES |
| Runtime | 9,309 ms | OBSERVED |
| Host notifications | 666 total: 665 event batches plus 1 summary | YES |
| Target events declared by VSE | 166,196 | YES |
| Target events reconstructed by Host | 166,196 | YES |
| Event index exported | First 8; last 2,818,379 | YES |
| Timestamp exported | First 67.664 us; last 17.506 sec | YES |
| Event type exported | All records _USB3_LINK_CMD | YES |
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

M2-PACKET-EXTRACTION-1 PASS for the bounded _USB3_LINK_CMD extraction slice
using batched Host delivery.

This proves that the selected decoded protocol event can cross the existing
VSE-to-COM-to-Host path with index, timestamp, and type preserved in a
verifiable JSON artifact. It does not prove complete packet extraction,
root-cause analysis, suspicious-region detection, comparison, or AI diagnosis.
