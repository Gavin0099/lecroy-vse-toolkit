# DEMO-I2: Immutable source qualification

## Objective

Verify that the customer-source preservation boundary is satisfied even if a
LeCroy working copy may be writable or otherwise subject to LeCroy behavior.
This probe first tests a read-only working copy. It does not open the source
artifact through VSE.

## Source selection

The source artifact was the pristine PASS trace extracted from the preserved
Desktop zip:

```text
E:\BackUp\Git_EE\_experiments\lecroy-vse-toolkit-governance-20260910\demo-i1-baseline\dp1 hub detect SSD Ex power ok-4.usb
```

The live Desktop PASS file was not used as the source for this probe because
its SHA-256 was already different from the preserved pristine artifact after
the earlier DEMO-I1 mutation observation.

## Procedure

```text
pristine source
    -> SHA-256 / size
    -> separate working copy
    -> IsReadOnly=True
    -> same M2-4 combined VSE extractor
    -> timeline JSON and read-back
    -> source SHA-256 / size verification
    -> working-copy SHA-256 / size verification
```

## Result

| Check | Result |
| --- | --- |
| Source before SHA-256 | `8D6B434C5AD0544C4DE57CB4C0B4111B75B8D57DD7B0F5F207626E4B938DFD77` |
| Source after SHA-256 | Same |
| Source size | `159,435,991` before and after |
| Working copy read-only | `True` |
| Working-copy before/after SHA-256 | Same as source |
| Working-copy size | `159,435,991` before and after |
| RunResult / FinishedResult | `2 / 2` |
| Notify count / summary count | `1,419 / 1` |
| Extracted events | `354,499` |
| Event counts | `LINK_CMD=353,289`; `LTSSM_STATE=35`; `LFPS=1,175` |
| JSON valid | `PASS` |
| JSON read-back match | `PASS` |
| Source evidence integrity | `PASS` |
| Working-copy integrity | `PASS` |

External run artifact:

```text
E:\BackUp\Git_EE\_experiments\lecroy-vse-toolkit-governance-20260910\demo-i2-readonly-1\output\demo-i2-readonly-pass-timeline.json
```

## Qualification boundary

This proves the source-preserving read-only path for this trace and the
selected LeCroy VSE / Automation configuration. It does not prove universal
immutability for every trace, LeCroy version, Windows policy, or execution
context.

The earlier writable-copy mutation remains retained as a known anomaly. The
product safety requirement is therefore defined as:

```text
SOURCE_EVIDENCE_INTEGRITY = PASS
```

It is not defined as a requirement that every disposable working copy remain
unchanged.
