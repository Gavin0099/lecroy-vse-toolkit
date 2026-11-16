# LeCroy Trace Integrity

Rule pack `lecroy`. Declare it in the governance contract output
(`RULES = common,lecroy`) for every non-L0 task in this repository; the domain
validators below only run when `lecroy` is an active rule.

Validators read evidence supplied in the post-task `checks` object. They check
that evidence is present and self-consistent; they cannot independently prove
that a trace was or was not modified.

## LECROY-TRACE-001 - no-trace-capture-in-change-set

- Source: PLAN.md "Rules for advancing" #3 (do not commit vendor samples or
  trace captures without an explicit license/handling decision).
- A change set must not contain LeCroy trace captures:
  `*.usb`, `*.usbtrace`, `*.uwb`, `*.utp`, `*.pex`.
- Exemption: `checks.trace_capture_decisions` maps the exact repo path to a
  recorded decision reference (for example a PLAN.md section).
- Validator: `governance/validators/lecroy_trace_integrity_validator.py`.
  Hard stop (`contract.yaml` `hard_stop_rules`).

## LECROY-TRACE-002 - trace-input-identity-evidence

- Source: M1-I1/I2 and the USB triage pipeline, which preserve the input
  trace's SHA-256, size and mtime and stop when they change.
- When a change touches code that opens or drives a raw trace, the checks must
  include one of:
  - `trace_identity`: a non-empty list of
    `{"trace": "<name>", "before_sha256": "<64 hex>", "after_sha256": "<64 hex>"}`
    with before == after for every entry (optional `before_size` /
    `after_size` must also match);
  - `trace_identity_not_applicable`: a non-empty reason that no trace was
    opened (reported as a warning).
- Any `trace_identity` entry whose hashes differ is a violation even when no
  trace-opening file changed.
- Trace-opening code (excluding `tests/**` and `*.md`): `*.vse`, `*.pevs`,
  `tools/*.cs`, `tools/run-*.ps1`, `tools/start-*.ps1`, `tools/run-*.py`,
  `tools/*_probe.py`, `tools/u01_selection.py`, `tools/usb_triage_pipeline.py`,
  `scripts/pcie/com_*.py`, `scripts/pcie/a1_com_*.py`,
  `scripts/pcie/run_pcie_triage.py`.
- Validator: `governance/validators/lecroy_trace_integrity_validator.py`.
  Hard stop.

## LECROY-DEL-001 - deletion-scope-declared

- Added file or directory deletion calls outside `tests/**` (for example
  `Remove-Item`, `rm -r`, `shutil.rmtree`, `os.remove`, `.unlink(`,
  `File.Delete`, `Directory.Delete`) require `checks.deletion_scope`: a
  non-empty statement of what is deleted and that raw traces and committed
  evidence are excluded.
- Detection is a text match on added diff lines (`checks.diff_text`), so it can
  produce false positives; it is advisory, not a hard stop. Irreversible
  deletions still need owner approval under the Agent Core Rules.
- Validator: `governance/validators/lecroy_deletion_scope_validator.py`.
