# M1-I1 trace mutation isolation record

## Scope

The test used four sacrificial copies derived from the current trace state.
The original customer trace was not used for any I1 stage.

```text
Baseline copy size:       103,062,189 bytes
Baseline copy SHA-256:    F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
Baseline LastWriteTimeUtc: 2026-09-10T07:01:12.5609905Z
```

Before each stage, the stage copy matched the baseline hash, size, and UTC
mtime. Each stage was compared again after completion using SHA-256, size, and
`LastWriteTimeUtc`.

## Negative evidence search

The repository Host/PowerShell/VSE sources were searched for:

```text
Trace.Save
.Save(
ApplyDisplayOptions
SetPersistentDecoding
AddComments
PersistentDecoding
Save(
```

No matches were found in `tools`, `scripts`, `docs`, `README.md`, or
`PLAN.md`. This is evidence about the repository code only; it does not prove
that the external Automation server cannot persist changes internally.

## Stage results

| Stage | Operation | Runtime/result | Before → after hash/size/mtime | Outcome |
| --- | --- | --- | --- | --- |
| I1-A | Automation `OpenFile()` → `Close()` → COM release | Open/Close succeeded; 5194 ms | Identical | PASS |
| I1-B | Open → COM2 full VSE traversal → close; no JSON | `DONE=2`, one notify, baseline counts; 6839 ms | Identical | PASS |
| I1-C | Open → COM2 traversal → Host JSON to separate output dir → close | `DONE=2`, one notify, write/read-back matched; 12609 ms | Identical | PASS |

All three stage copies retained this identity after their respective runs:

```text
SHA-256: F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F
Size:    103,062,189 bytes
mtime:   2026-09-10T07:01:12.5609905Z
```

The I1-C artifact was written outside the trace directory:

```text
C:\Users\reiko\Desktop\Lecory\m1-i1-sandbox\output-c\summary.json
```

It contained the four expected fields and passed read-back verification.

## Interpretation

```text
I1-A unchanged  → OpenFile/Close alone did not reproduce the mutation
I1-B unchanged  → COM2 VSE traversal did not reproduce the mutation
I1-C unchanged  → Host JSON output to a separate directory did not reproduce it
```

The earlier mutation of the original trace remains real historical evidence,
but its cause is still UNKNOWN. It was not reproduced under the three
controlled sacrificial-copy conditions. This does not prove universal
read-only behavior for every LeCroy version, trace state, GUI state, or
Automation context.

## Verdict

`M1-I1 controlled isolation PASS`.

`M1 input integrity` is improved but not closed: controlled A/B/C runs were
unchanged, while the original COM3 mutation remains unexplained. Keep the
clean baseline, Governance adoption, and M2 triage work on HOLD until that
historical discrepancy has an explicit disposition. A production immutable
input hash guard remains a future requirement and is not implemented here.

Follow-up `M1-I2` reproduced the original same-folder COM3 layout on a fresh
sacrificial copy and also preserved hash, size, and UTC mtime. See
`exact-com3-integrity-results.md` for the final controlled qualification.
