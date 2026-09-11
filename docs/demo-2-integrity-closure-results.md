# DEMO-2 integrity closure

## Objective

Close the DEMO-1 PASS working-copy integrity hold without widening the
analysis claim. The runner must preserve the source traces, keep both
disposable analysis copies read-only, and expose enough evidence for the
acceptance decision to be replayed from its output artifacts.

## Implementation boundary

`run-demo.ps1` now snapshots SHA-256, size, UTC mtime, and read-only state for
the two source traces and the two disposable working copies. The runner writes
`source-integrity.json` before comparison and requires all of the following:

- both source traces unchanged;
- both working copies unchanged;
- both working copies read-only before and after extraction; and
- `analysis_input_integrity=true`.

The Windows PowerShell 5.1 compatibility harness asserts these fields instead
of checking only the source-level boolean.

## Controlled verification

The known repository-relative inputs were used:

```text
dp1 hub detect SSD Ex power ok-4.usb
dp1 hub detect SSD fail-2.usb
```

| Check | Result |
| --- | --- |
| pwsh end-to-end runner | PASS |
| Windows PowerShell 5.1 qualification harness | PASS |
| Existing-output refusal | PASS |
| PASS source integrity | PASS |
| FAIL source integrity | PASS |
| PASS working-copy read-only before/after | `True / True` |
| FAIL working-copy read-only before/after | `True / True` |
| PASS working-copy integrity | PASS |
| FAIL working-copy integrity | PASS |
| Combined analysis-input integrity | PASS |
| PASS timeline | `354,499` events; JSON/read-back/order checks PASS |
| FAIL timeline | `213,232` events; JSON/read-back/order checks PASS |
| Common anchor | FOUND, length 5 |
| Candidate comparison | EVALUATED_AFTER_ANCHOR |

The source identities remained stable in the closure run:

```text
PASS SHA-256: 8D6B434C5AD0544C4DE57CB4C0B4111B75B8D57DD7B0F5F207626E4B938DFD77
FAIL SHA-256: A5568248D1C3D04F3CC16D6D3649F1303BE0D15FFA1A734E2057D73564836CAE
```

## Disposition

The working-copy integrity hold is resolved for the selected
source-preserving runner mode. The earlier writable-copy mutation remains a
known unexplained anomaly. This result does not claim universal immutability
for every trace, LeCroy version, Windows policy, or execution context.

M3 transfer reconstruction remains not started. The next slice must first
confirm the required transfer-level event fields and define replayable grouping
fixtures; the presence of the `_XFER` selection level alone is not transfer
reconstruction evidence.
