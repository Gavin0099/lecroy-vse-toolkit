# USB / PCIe workflow parity baseline — 2026-10-19

Baseline: bde60d9dfa6132bc4e9e8876ba70d70a5766ed8a plus the preserved local
PCIE-01/02A/03 implementation. User plan is preserved byte-for-byte in
`pcie-usb-workflow-parity-plan-20261019.md`. This matrix records the implementation
contract; actual validation results are recorded separately.

| Interaction | Existing USB behavior | PCIe target / intentional exception |
|---|---|---|
| Entry | One native WinForms workspace, Ctrl+O / picker / drop | Same window and handlers; `.usb` and `.pex` |
| Preparation | One input, fresh job, readonly copy, source SHA | Same identity rules; converted numbering remains separate |
| Background | Python controller, independent native worker, polled status | Reuse controller; PCIe extraction stays in its own module |
| Busy | Reject second import; controls disabled, marquee | Same; cancel only at verified safe stage boundaries |
| Discovery | USB2 / USB3 / PD independent engines | Existing G1/G2/G3/G9 only; no frozen W1–W5 injection |
| Results | Left candidates, right facts/reasons/next/context/limits | Same controls; PCIe Packet/direction/raw BDF; unknown stays unknown |
| Default list | At most three per protocol; total count | First three in explicit capture order; reveal all available candidates |
| Empty | No candidates does not imply USB PASS | No candidates does not imply PCIe PASS; coverage still visible |
| Native location | GotoUnit; PKT/TRA/XFR view may need manual switch | Open verified working copy; Ctrl+G manual instructions, not GUI one-click |
| Failure | Visible error, recovery, logs, copy location | Same; existing PETracer is blocked without attaching/closing |
| Export | Offline HTML from inspection model | Same entry, PCIe HTML / Markdown from same inspection model |
| End | Close owned trace, verify integrity; keep evidence | Same ownership boundary; never kill native application on timeout |

## State and data contract

Idle -> preparing/importing -> extracting -> verifying/analyzing -> complete or
no_candidates. Partial and failed results show coverage/error, not stale candidates.
An accepted import clears the prior model before new work. Rejected concurrent
imports keep the current run. Native operation failure does not invalidate a
completed analysis, but disables unconfirmed navigation until recovery.
Cancellation is cooperative between native calls; active COM calls are not
claimed cancelled. Timeout stops only the owned Python worker and preserves the
working copy; native state stays unknown.

PCIe has its own `pcie-triage-inspection/v1` boundary model. It shares presentation
keys with USB without making PCIe a USB protocol or fabricating nanosecond time.
Source/display SHA, namespace, analysis ID, coverage, evidence references and
manual navigation state are carried to every candidate and export.

## Protected analysis surfaces

Do not edit `usb_control_triage.py`, `usb3_triage.py`, `pd_triage.py`,
`usb_triage_model.py`, USB VSE scripts, or the G1/G2/G3/G7/G8/G9 PCIe rules.
The frozen W1–W5 worktree at f417eecb340f56d09d6e4c0ca0b86f81e2977181 is
read-only dependency evidence, never a candidate source for imported traces.
Shared controller, native form and portable builder may change at the boundary.

## Baseline validation

Before editing: PCIe 243, desktop controller 51, USB2 31 tests pass.
Windows screenshots and final positive/negative regression results will be
listed in the parity results document. Automated UI inspection is not engineer
usability acceptance. PCIE-05 requires an unfamiliar trace and a real engineer.
