# DEMO-1: PASS vs FAIL candidate comparison

## Status

`QUALIFIED — CONTROLLED SOURCE-PRESERVING READ-ONLY MODE`

The combined extractor and comparison path ran successfully. The original
Demo run mutated its PASS working copy, so DEMO-I1 localized that mutation.
DEMO-I2 then qualified the source-preserving architecture by keeping the
preserved source artifact outside the VSE execution path and running the same
extractor against a separate read-only working copy.

## Inputs

- PASS candidate: `dp1 hub detect SSD Ex power ok-4.usb`, restored from the
  Desktop zip into a sacrificial Demo copy.
- FAIL candidate: `dp1 hub detect SSD fail-2.usb`, copied into a sacrificial
  Demo directory.
- Extractor: scripts/m2-packet-extraction-4.vse.
- Host harness: tools/run-m2-timeline-extraction.ps1.
- Comparator: tools/compare-m2-timelines.ps1.
- Timeline and comparison JSON were written outside the repository.

Both traces used the same combined extractor and one VSE traversal per trace.
The comparator did not compare absolute timestamps directly. It searched for a
unique common five-event sequence anchor, then compared normalized event
signatures after that anchor.

## Combined extraction

| Event class | PASS | FAIL |
| --- | ---: | ---: |
| _USB3_LINK_CMD | 353,289 | 166,196 |
| _USB3_LTSSM_STATE | 35 | 30 |
| _USB3_LFPS | 1,175 | 47,006 |
| Total | 354,499 | 213,232 |

Both runs completed with `RunResult=2`, `FinishedResult=2`, valid JSON,
complete Host reconstruction, and chronological event-index ordering.

## Integrity qualification

### DEMO-I2 source-preserving read-only run

The source artifact for this controlled probe was the pristine PASS trace
extracted from the Desktop zip. The live Desktop PASS file was not used as the
source for this run because its SHA-256 no longer matched the preserved
pristine artifact after the earlier mutation observation.

- Source before and after SHA-256:
  `8D6B434C5AD0544C4DE57CB4C0B4111B75B8D57DD7B0F5F207626E4B938DFD77`
- Source size: `159,435,991` before and after
- Working copy: separate file with `IsReadOnly=True`
- Working-copy before and after SHA-256: same as source SHA above
- Working-copy size: `159,435,991` before and after
- RunResult / FinishedResult: `2 / 2`
- Notify count: `1,419`; summary count: `1`
- Extracted events: `354,499`
- Counts: `LINK_CMD=353,289`, `LTSSM_STATE=35`, `LFPS=1,175`
- JSON valid and read-back match: `PASS`
- Working-copy integrity unchanged: `PASS`

This establishes the source-preserving read-only path for this trace and the
selected VSE/Automation configuration. It does not claim universal behavior
for every trace, LeCroy version, Windows policy, or execution context.

### PASS candidate

- Before SHA-256: `8D6B434C5AD0544C4DE57CB4C0B4111B75B8D57DD7B0F5F207626E4B938DFD77`
- After SHA-256: `0B2131B25441E9EB68D770C8CF70237AF0E944423477E723FD428EEF39A1F062`
- Size: `159,435,991` -> `159,436,011`
- Result: `FAIL`

The same `+20` size delta occurred when the VSE run used the pristine copy
restored from the Desktop zip. DEMO-I1 localized that run to `307` changed
byte positions across `15` ranges, including existing content and a `20`-byte
appended tail. This is recorded as a product pipeline blocker; the original
zip remains the preserved source artifact.

### FAIL candidate

- Before and after SHA-256: `F94E3E60D68F08A90104B3D11ECE6A89F0E34649BCFB5F0C616DD4F765D8540F`
- Before and after size: `103,062,189`
- Result: `PASS`

## Candidate divergence

- Common anchor: found, length 5.
- PASS anchor index: 5.
- FAIL anchor index: 125,356.
- Candidate PASS timestamp: `2.189 sec`.
- Candidate FAIL timestamp: `13.998 sec`.
- Suggested PASS GUI window: `2.000 sec` to `2.289 sec`.
- Suggested FAIL GUI window: `14.000 sec` to `14.098 sec`.

The tool reports this as `candidate divergence`. It does not claim absolute
first divergence, direct timestamp alignment, root cause, severity, or PASS /
FAIL classification. The two timestamps are trace-local because the captures
may have different start offsets.

## Verdict

The first comparison Demo has demonstrated the intended product shape:

```text
PASS trace + FAIL trace
    -> same combined extractor
    -> normalized timelines
    -> common-anchor comparison
    -> candidate GUI inspection windows
```

The Demo is qualified only within the controlled source-preserving read-only
mode described above. The prior writable-copy mutation remains retained as a
known anomaly, and no new protocol decoder, AI diagnosis, severity, or
root-cause claim is added.
