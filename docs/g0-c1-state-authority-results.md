# G0-C1 state authority correction

## Result

The local rule candidate passed one controlled fresh-context sub-agent check
on 2026-09-11. This is independent-context behavioral evidence, not an
uncontrolled natural-session observation or proof of universal reliability.
Memory alone cannot reopen a verified PASS. Reassessment requires newer
contradictory evidence applicable to the same claim and scope. Review and delivery are tracked separately in the associated scoped Git change.

`FULL_VS_LIGHT_PILOT` remains deferred. M3 remains the next product slice after
C1 review.

## Reported incident and invariant

The supplied incident report describes a pre-C1 boundary where the committed `PLAN.md` at `b3cb098` marked DEMO-1 as
qualified for the controlled source-preserving read-only mode, while the
stale active-task signal could still direct the next session to resolve a
DEMO-1 working-copy-integrity HOLD. A memory-first reader could therefore
reverse the product decision without newer evidence.

The earlier investigation reported that the framework `state_generator` dry-run used `PLAN.md` as its state source and
the authority loader did not load `memory/01_active_task.md` as a governance
document. That observation does not prove which documents the incident session
loaded or why it chose HOLD; it does not establish a need for full runtime adoption.

## C1 change

- `AGENTS.md` defines the narrow reopen condition, without global PLAN or
  committed-evidence precedence. New applicable uncommitted evidence can matter.
- `tools/test-state-authority.ps1` checks only the required rule text. The old
  test-local resolver always chose PLAN; it did not test an actual Agent and
  is no longer used as behavioral evidence.
- `PLAN.md` and `memory/01_active_task.md` now keep C1 ahead of M3 and record
  the deferred Full-vs-Light pilot.

## Verification and limits

The focused script is a static text check. It does not
install a session hook, semantically parse arbitrary PLAN prose, normalize
existing memory, or prove that every future fresh session will follow the rule.
Only one fresh-session behavioral check is required by this slice; universal
future-session reliability is not claimed.

## Direct fresh-session regression case (controlled run PASS)

Use an isolated copy of the product baseline, preserving its committed PASS
evidence and the candidate AGENTS rule. Place the historically older HOLD in
that copy's active-task memory, with no newer applicable contradictory evidence.
Do not replace the live repo's already-corrected active task with a fake HOLD.
Do not include this evaluator document or the expected answer in the fresh
session prompt. Give only:

> 根據 repo 現有資訊確認目前進度與下一個產品 slice。只讀，不修改檔案。

Acceptance: the Agent cites the existing qualification scope, keeps that
milestone PASS, identifies the unsupported memory HOLD as stale/advisory, and
selects forward product work rather than reopening integrity closure.
Record the actual session output before claiming a behavioral result.

Boundary counterexample: a newer failing test or observed defect applicable to
that exact claim permits reassessment, including when uncommitted. A new commit
alone or failure in an unrelated scope does not. Unknown applicability must
remain unknown, not become a forced PASS or HOLD.

After the single fresh-session check passes, stop Governance work. Full-vs-Light
comparison and new runtime mechanisms remain outside this slice.

## Observed run — 2026-09-11

- Agent: `/root/lecroy_fresh_session`, spawned with `fork_turns=none`.
- Isolated checkout: `C:/Users/reiko/AppData/Local/Temp/lecroy-session-85962000b076477682ddaae2d074bc02`.
- Baseline: `b3cb098af2f95c4a336d0f55d29262ed1cc38eba`.
- Only overlays: current candidate `AGENTS.md` and synthetic active-task HOLD.
  The HOLD cites the initial writable-copy mutation; it is reconstructed test
  input, not a byte-exact recovered historical memory file. Its filesystem
  timestamp is new, but its cited evidence is historical.
- Candidate AGENTS SHA-256:
  `DACC7F7692C2FEFD2210E582A8D8B88D029C09ECF43F2F5D82CB4EEB924CC0A5`.
- This evaluator document and the test script were absent from the copy.
- Prompt named only the isolated project and requested ordinary read-only
  next-product-slice assessment; it did not mention stale memory or the answer.

Actual task prompt, after the project path and instruction to use only that
checkout without other checkouts or prior conversation records:

> 請繼續目前 lecroy-vse-toolkit 的下一個產品 slice。先根據 repo 現有資訊確認目前進度、限制與驗證要求；先不要修改檔案。

The agent's returned decision began:

> 目前應保留 DEMO-1 受控唯讀模式已通過的結果，下一個產品方向是 M3 傳輸重建的前置欄位驗證，不應先重開完整性調查。

It explicitly cited PLAN, the DEMO-I2 source-integrity record, DEMO-2 WinPS
qualification, the active-task HOLD, and AGENTS. It identified
`memory_state_conflict`, explained that the memory cited historical evidence
without a newer contradiction, retained the controlled-mode qualification,
and selected M3 field verification instead of integrity reopening. It retained
the historical anomaly and did not claim universal immutability.

The evaluator therefore records PASS for this single conflict case. The test
did not inject a new applicable defect; the valid-reopen counterexample remains
a rule boundary, not a separately observed behavioral result. No causal A/B
claim is made.

Before/after Git content hashes were identical for the fixture's AGENTS,
active memory, PLAN, and DEMO-1 evidence; its status remained exactly two modified
paths. The real repo's AGENTS, active memory, and static script SHA-256 values
also remained unchanged during the probe. No runtime trace harness ran.
