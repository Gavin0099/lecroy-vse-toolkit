# Governance adoption boundary

This repository has two independent decisions:

1. M1 proves the LeCroy VSE execution path.
2. G0 adopts AI Governance as a separate repository/process slice.

They must not be treated as one experiment.

## Canonical source

```yaml
repository: https://github.com/Gavin0099/ai-governance-framework
branch: main
baseline_commit: NOT_SELECTED
```

GitHub is the canonical source, but `main` moves. A reproducible adoption source is the canonical repository plus an explicitly recorded commit SHA. Until that SHA is selected, there is no pinned Governance baseline for this repo.

The local checkout at `E:\BackUp\Git_EE\ai-governance-framework` is currently dirty and contains unrelated working changes/untracked paths. It must not be used as the adoption source.

## Why G0 follows M1

M1 has a small causal chain:

```text
trace-info.vse
    -> LeCroy VSE
    -> VSTools.inc
    -> real .usb trace
    -> trace summary
```

Governance adoption introduces another layer of variables, including instruction files, contracts, baseline metadata, hooks, validators, and memory surfaces. If it is added before M1, a failure no longer identifies whether the VSE path or the adoption path is responsible.

The gate is therefore:

```text
M1 real-trace PASS
    -> G0 source SHA selection
    -> adoption --dry-run
    -> predicted-change review
    -> separate governance commit/PR
```

## G0 procedure when authorized

1. Obtain a clean checkout or worktree from the canonical GitHub repository.
2. Record the exact framework commit SHA.
3. Run `adopt_governance.py --dry-run` against this repo.
4. Review the predicted files and topology.
5. Apply only the approved adoption slice.
6. Verify adoption artifacts separately from runtime governance behavior.

Copy-based adoption can establish an audit surface, but it does not by itself prove that hooks execute, decisions fail closed, or memory is restored in a later session.

## Current state

```yaml
m1_runtime_proof: pending
g0_adoption: deferred
framework_baseline_sha: not_selected
target_has_framework_root: false
target_has_governance_hook: false
```
