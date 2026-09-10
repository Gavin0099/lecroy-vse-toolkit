# DEMO-2-WINPS-COMPAT: Windows PowerShell 5.1 qualification

## Objective

Qualify the exact execution path used by the Demo on a fresh
`powershell.exe` process, including the legacy `Add-Type` compiler and the
COM host invocation.

## Host

```text
Executable: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
Version:    5.1.26100.9444
Edition:    Desktop
CLR:        4.0.30319.42000
```

## Acceptance

| Check | Result |
| --- | --- |
| C# `Add-Type` compile | `PASS` |
| `run-demo.ps1` parse | `PASS` |
| `run-m2-timeline-extraction.ps1` parse | `PASS` |
| Existing-output refusal | `PASS` |
| Full runner exit code | `0` |
| Source evidence integrity | `PASS` |
| Common anchor | `FOUND` |
| Candidate comparison | `EVALUATED_AFTER_ANCHOR` |

The exact repository-relative inputs were used:

```text
./dp1 hub detect SSD Ex power ok-4.usb
./dp1 hub detect SSD fail-2.usb
```

The resulting event totals were `354,499` for PASS and `213,232` for FAIL.
The source traces were only hashed; VSE received separate read-only sandbox
copies.

## Compatibility implementation boundary

The COM host avoids `dynamic` so the runner does not depend on an implicit
`Microsoft.CSharp.RuntimeBinder` reference. COM methods and properties are
invoked through `Type.InvokeMember`, and the C# source uses legacy-compatible
constructs accepted by the Windows PowerShell `Add-Type` compiler.

## Observation boundary

The Windows PowerShell comparator used materially more memory and took longer
than the pwsh self-test for this large event set. This is a performance
observation, not a correctness failure and is not yet a formal M5 benchmark.
