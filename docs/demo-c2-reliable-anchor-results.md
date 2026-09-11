# DEMO-C2 Reliable Common Anchor Results

Date: 2026-09-11

## Objective

Prevent the PASS/FAIL comparator from accepting a coincidental short sequence
as a common anchor. If the evidence is not strong enough, the comparator must
return `NO_RELIABLE_COMMON_ANCHOR` and must not emit a GUI inspection window.

## Scope

This slice changes only comparator confidence gating and the human-readable
report. It does not add protocol event classes, infer LFPS enum names, change
timestamp precision, or claim root cause.

An anchor candidate must have:

- a stable event signature, including available LFPS raw fields;
- one occurrence in each timeline;
- matching ten-event pre-context; and
- matching five-event post-context.

The existing event ordering and trace-preserving extraction path are reused.

## Qualification command

The exact Windows PowerShell 5.1 qualification was run with the repository
copies of the known PASS/FAIL traces:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\tools\test-demo2-winps-compat.ps1 `
  -PassTrace ".\dp1 hub detect SSD Ex power ok-4.usb" `
  -FailTrace ".\dp1 hub detect SSD fail-2.usb" `
  -Output ".\demo-output-c2-qualification-20260911"
```

## Observed result

| Check | Result |
| --- | --- |
| Windows PowerShell | 5.1.26100.9444 / Desktop |
| Add-Type compile | PASS |
| Script parsing | PASS |
| Full runner exit | 0 |
| Source evidence integrity | PASS |
| Working-copy integrity | PASS |
| Analysis input integrity | PASS |
| PASS event total | 354,499 |
| FAIL event total | 213,232 |
| Unique anchor candidates rejected | 28 |
| Anchor status | `NO_RELIABLE_COMMON_ANCHOR` |
| Candidate status | `NO_RELIABLE_COMMON_ANCHOR` |
| GUI window | Not produced |

The prior false anchor (`PASS index 5` / `FAIL index 125356`) was rejected
because it did not have sufficient pre-context. No replacement candidate was
accepted.

## Claim boundary

This is a C2 fail-closed qualification for the known pair. It proves that the
comparator no longer turns the previously observed weak anchor into a GUI
recommendation. It does not prove that the comparator can yet find the actual
failure region at approximately 21.789--21.801 seconds, and it does not claim
that no reliable anchor exists for other trace pairs.

Timestamp precision and improved alignment remain separate follow-up work.
