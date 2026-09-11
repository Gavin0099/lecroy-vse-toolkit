# DEMO-C4 Semantic Alignment

## Objective

Use the expert-labeled FAIL region and the verified VSE raw fields to look for
the corresponding protocol phase in the PASS timeline. This slice must not
align captures by absolute timestamps, infer LFPS enum names, or emit a GUI
window when the semantic evidence is not unique.

## Method

The fingerprint is centered on the first verified raw LFPS seed inside the
expert-labeled FAIL region:

```text
FAIL region: 21.789454560--21.801473168 sec
LfpsType: 74
DurationNs: 2200
PatternType: 4
StartsPattern: 1
```

The fingerprint contains twelve events before and twelve events after the
seed. It uses the event class/type, the available LFPS raw fields, and relative
timestamp gaps quantized to 1,000 ns. It does not use absolute timestamps to
align the two captures.

The raw numeric values remain uninterpreted. In particular, this document does
not claim that `LfpsType=74` has a particular protocol name.

## Result

The result is produced by:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\compare-c4-semantic-timelines.ps1 `
  -PassTimelinePath <pass-timeline-with-timestamp-ns.json> `
  -FailTimelinePath <fail-timeline-with-timestamp-ns.json> `
  -OutputPath <c4-output>\semantic-alignment.json
```

The status is one of:

- `SEMANTIC_MATCH_FOUND`
- `MULTIPLE_SEMANTIC_MATCHES`
- `NO_RELIABLE_SEMANTIC_MATCH`
- `SEMANTIC_COVERAGE_INSUFFICIENT`

Only `SEMANTIC_MATCH_FOUND` emits a GUI handoff. The other statuses are
fail-closed outcomes and do not produce PASS/FAIL GUI correspondence.

The known-pair qualification produced:

| Check | Result |
| --- | --- |
| Windows PowerShell 5.1 path | PASS |
| PASS/FAIL timeline extraction | PASS |
| Timestamp components present | `true` |
| Timeline trace integrity | `true` |
| FAIL seed occurrences in ground-truth region | `314` |
| FAIL fingerprint matches | `1` |
| PASS fingerprint matches | `0` |
| Semantic result | `NO_RELIABLE_SEMANTIC_MATCH` |
| GUI handoff | Not emitted |

The fail-closed result is the intended C4 behavior for this evidence set. It
proves that the comparator does not guess a PASS correspondence when the
verified semantic fingerprint is absent. It does not prove that the correct
PASS protocol phase is absent, and it does not yet qualify useful automatic
semantic alignment.

The generated artifact is:

`c4-output-20260911/semantic-alignment.json`

## Claim boundary

This slice does not claim root cause, severity, automatic PASS/FAIL
classification, universal semantic alignment, or that the selected raw LFPS
values have decoded names. If the PASS phase is absent or ambiguous, the tool
must report that limitation instead of widening the matching threshold.
