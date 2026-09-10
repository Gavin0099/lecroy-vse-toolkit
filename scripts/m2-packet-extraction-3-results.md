# M2-PACKET-EXTRACTION-3: USB3 LFPS event and field extraction

## Scope

- Input: the same real trace on a sacrificial copy.
- Target event: installed LeCroy decoded _USB3_LFPS.
- VSE script: scripts/m2-packet-extraction-3.vse.
- Host harness: tools/run-m2-lfps-extraction.ps1.
- Output: host-owned lfps-batched-1.json outside the repository.
- Exported event fields: index, timestamp text, and event type.
- Exported LFPS fields: Type, Duration, DurationSec, DurationNS, PatternType,
  and StartsPattern.
- Field values remain raw numeric observations. No LFPS type or pattern name
  mapping is inferred by this repository.
- Excluded: severity, suspicious, root cause, GUI recommendation, comparison,
  and AI explanation.

The official VSE documentation identifies _USB3_LFPS as the USB3 Low
Frequency Periodic Signaling event and documents these LFPS-specific input
context members. The result below is still qualified by the installed 10.40
runtime observation rather than by documentation alone.

## Delivery configuration

The installed 10.40 VSE files did not expose a usable SendTraceEventOnly().
The script therefore reuses the M2-1/M2-2 delivery configuration and filters
in ProcessEvent() by _USB3_LFPS.

## Acceptance

| Check | Evidence | Outcome |
| --- | --- | --- |
| Real trace used | Fresh sacrificial copy of dp1 hub detect SSD fail-2.usb | YES |
| Existing M2 delivery configuration reused | Same channel, level, and trace-event selection | YES |
| VSE completes | RunResult=2, FinishedResult=2 | YES |
| Runtime | 6,626 ms | OBSERVED |
| Host notifications | 190 total: 189 event batches plus 1 summary | YES |
| Target events declared by VSE | 47,006 | YES |
| Target events reconstructed by Host | 47,006 | YES |
| Event index exported | First 629,253; last 3,174,658 | YES |
| Timestamp exported | First 13.897 sec; last 22.166 sec | YES |
| Event type exported | All records _USB3_LFPS | YES |
| LFPS Type exported | Raw numeric values observed | YES |
| Duration exported | DurationNs plus DurationSec/DurationNS observed | YES |
| Pattern fields exported | PatternType and StartsPattern observed | YES |
| JSON exists and is valid | Host write plus ConvertFrom-Json read-back | YES |
| Read-back match | Count and event records matched | YES |
| Event fields valid | Required and LFPS-specific fields present for every record | YES |
| Trace integrity | SHA-256, size, and UTC mtime unchanged | YES |

## Observed distributions

- LFPS Type raw values: 65=3, 66=2, 68=41,839, 71=2, 72=4,009,
  73=575, 74=576.
- PatternType raw values: 0=18, 1=41,764, 2=64, 4=5,041, 5=119.
- StartsPattern: 0=35,976; 1=11,030.
- DurationNs minimum: 8.
- DurationNs maximum: 99,999,896.

These are observations from this trace, not protocol-name mappings or failure
classification.

## Trace integrity

Before SHA-256: F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
After SHA-256:  F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F

Before size: 103062189
After size:  103062189

Before mtime UTC: 2026-09-10T07:01:12.5609905Z
After mtime UTC:  2026-09-10T07:01:12.5609905Z

## Verdict

M2-PACKET-EXTRACTION-3 PASS for the bounded _USB3_LFPS extraction slice with
LFPS-specific fields preserved through the existing batched VSE -> COM -> Host
path and verified in JSON read-back.

This proves the current 10.40 runtime exposed the selected LFPS fields for
this trace. It does not prove complete LFPS decoding, semantic names for raw
enum values, triage, comparison, or AI diagnosis.
