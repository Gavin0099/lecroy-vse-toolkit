#!/usr/bin/env python3
"""PCIe-G9a/G9b/G9c: thin offline triage runner.

Input is an already verified extraction bundle (G2a fields, G3c-0 messages, optional GUI
cross-checks) described by an input manifest. The runner validates it (fail closed), calls the
existing stage CLIs in order (G2b, G3a/b, G3c, G3d, G3e, G3f, G7, G8) and writes an engineer
review package with a run manifest. It does not open traces, drive PETracer, use COM or run VSE.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import g2b_associate  # noqa: E402
import g3_candidates  # noqa: E402
import g3c_nearby_messages  # noqa: E402
import g3d_context  # noqa: E402
import g3e_groups  # noqa: E402
import g3f_findings  # noqa: E402
import g7_render_markdown  # noqa: E402
import g8_render_html  # noqa: E402

INPUT_SCHEMA = "pcie.triage-input/v1"
RUN_SCHEMA = "pcie.triage-run-manifest/v1"
PARAMETERS = {"g3c_window_tlp_rows": 8, "g3c_max_packet_gap": 64, "g3d_context_rows": 5}
SHA_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
STAGE_SCRIPTS = {
    "runner": "run_pcie_triage.py", "g2b": "g2b_associate.py", "g3ab": "g3_candidates.py", "g3c": "g3c_nearby_messages.py",
    "g3d": "g3d_context.py", "g3e": "g3e_groups.py", "g3f": "g3f_findings.py", "g7": "g7_render_markdown.py", "g8": "g8_render_html.py",
}


class TriageError(ValueError):
    """Input validation or a stage failed; no report is claimed."""

    def __init__(self, message: str, stage: str) -> None:
        super().__init__(message)
        self.stage = stage


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _resolve(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _load_json(path: Path, stage: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TriageError(f"cannot read JSON {path}: {exc}", stage) from exc


def validate_inputs(manifest: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """G9b: accept only a complete, self-consistent, verifier-passed extraction bundle."""
    stage = "validate_inputs"
    if manifest.get("schema_version") != INPUT_SCHEMA:
        raise TriageError(f"input manifest schema must be {INPUT_SCHEMA}", stage)
    trace = manifest.get("trace") or {}
    if not trace.get("file_name") or not SHA_RE.fullmatch(str(trace.get("sha256", ""))) or type(trace.get("tlp_count")) is not int or trace["tlp_count"] <= 0:
        raise TriageError("trace needs file_name, a 64-hex sha256 and a positive integer tlp_count", stage)

    def checked(section: str, required: bool = True) -> Path | None:
        entry = manifest.get(section)
        if not entry:
            if required:
                raise TriageError(f"missing input section {section}", stage)
            return None
        path = _resolve(repo_root, entry["path"])
        if not path.is_file():
            raise TriageError(f"{section} file missing: {path}", stage)
        actual = sha256(path)
        if actual != str(entry.get("sha256", "")).upper():
            raise TriageError(f"{section} SHA-256 {actual} differs from the input manifest", stage)
        return path

    fields_path = checked("fields")
    messages_path = checked("messages")
    crosschecks_path = checked("gui_crosschecks", required=False)
    fields_sha = sha256(fields_path)
    messages_sha = sha256(messages_path)

    fields_summary_path = _resolve(repo_root, manifest["fields"]["verifier_summary"])
    fields_summary = _load_json(fields_summary_path, stage)
    if fields_summary.get("status") != "PASS_FIELD_PROBE_OUTPUT":
        raise TriageError("G2a verifier summary status is not PASS_FIELD_PROBE_OUTPUT", stage)
    if str(fields_summary.get("fields_json_canonical_sha256", "")).upper() != fields_sha:
        raise TriageError("G2a verifier summary does not describe this fields.json", stage)
    if fields_summary.get("rows") != trace["tlp_count"]:
        raise TriageError(f"G2a verifier rows {fields_summary.get('rows')} differ from trace tlp_count {trace['tlp_count']}", stage)
    fields = _load_json(fields_path, stage)
    if not isinstance(fields, list) or len(fields) != trace["tlp_count"]:
        raise TriageError("fields.json row count differs from trace tlp_count", stage)

    messages_summary = _load_json(_resolve(repo_root, manifest["messages"]["verifier_summary"]), stage)
    if messages_summary.get("status") != "PASS_MESSAGE_FIELD_PROBE_OUTPUT":
        raise TriageError("G3c-0 verifier summary status is not PASS_MESSAGE_FIELD_PROBE_OUTPUT", stage)
    if str(messages_summary.get("messages_json_sha256", "")).upper() != messages_sha:
        raise TriageError("G3c-0 verifier summary does not describe this messages.json", stage)
    if str(messages_summary.get("g2a_fields_sha256", "")).upper() != fields_sha:
        raise TriageError("messages.json was verified against a different fields.json (other extraction or trace)", stage)

    return {"trace": trace, "fields": fields_path, "messages": messages_path, "gui_crosschecks": crosschecks_path,
            "fields_summary": fields_summary_path}


def run_stage(name: str, func: Callable[[list[str]], int], argv: list[str], expected: list[Path]) -> dict[str, Any]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = func(argv)
    except Exception as exc:  # a stage crash is a stage failure, never a partial success
        raise TriageError(f"{name} raised {type(exc).__name__}: {exc}", name) from exc
    missing = [p.as_posix() for p in expected if not p.is_file()]
    if code != 0 or missing:
        raise TriageError(f"{name} failed (exit {code}, missing {missing}): {err.getvalue().strip()[:400]}", name)
    return {"stage": name, "status": "PASS", "outputs": {p.name: sha256(p) for p in expected}}


README_TEMPLATE = """# PCIe Trace 候選檢查位置報告，使用說明

Run id `{run_id}`，trace `{trace_name}`（SHA-256 `{trace_sha}`）。

## 先開哪個檔案

打開 `report.html`。最上面是閱讀前須知，接著是 {findings} 組候選檢查位置的一覽表，下面每一組一張卡片。
卡片第一層有主要定位點、觀察摘要和各 Segment 的時間，按「展開完整證據」可以看到 packet 細節、限制和追溯。
`report.md` 是同樣內容的純文字版。

## 在 LeCroy 對照

在 PETracer 打開同一份 trace（SHA-256 應為 `{trace_sha}`），用 Search > Go to Packet（Ctrl+G）輸入卡片上的 packet 編號。
主要定位點依固定規則選出，只用來跳轉，不代表該位置比較嚴重。

## 這份報告的限制

- 這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷故障原因。
- 附近 message 只代表位置接近，判斷附近用的 64 packets 範圍是暫定條件。
- 分在同一組代表 evidence 有關聯，不代表屬於同一個故障事件。

## 回饋時請附上

- Run id `{run_id}` 和 finding 編號，例如 `F009`。
- 這一組位置有沒有幫你更快找到要看的地方。
- 你實際 debug 時還需要看哪些資訊，而報告沒有列出。

## 資料夾內容

- `report.html`、`report.md`，給人看的報告。
- `findings.json`，報告的唯一資料來源。
- `run-manifest.json`，這次產出用了哪些輸入、script 與參數，以及各檔 SHA-256。
- `stages/`，中間產物，用來追查單一 finding 的來源。
"""


def run(input_manifest_path: Path, output_dir: Path, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    if output_dir.exists():
        raise TriageError(f"output directory already exists: {output_dir}", "validate_inputs")
    manifest_raw = input_manifest_path.read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8"))
    started = datetime.now(timezone.utc)
    run_manifest: dict[str, Any] = {
        "schema_version": RUN_SCHEMA,
        "started_utc": started.isoformat(timespec="seconds"),
        "status": "FAILED",
        "input_manifest": {"path": input_manifest_path.as_posix(), "sha256": hashlib.sha256(manifest_raw).hexdigest().upper()},
        "parameters": PARAMETERS,
        "python": platform.python_version(),
        "script_sha256": {k: sha256(SCRIPT_DIR / v) for k, v in STAGE_SCRIPTS.items()},
        "excluded": ["PETracer GUI automation", "COM", "opening .pex files", "running VSE scripts", "legacy format conversion", "AI agent", "writing skill"],
        "stages": [],
    }
    output_dir.mkdir(parents=True)
    try:
        inputs = validate_inputs(manifest, repo_root)
        trace = inputs["trace"]
        run_manifest["trace"] = trace
        run_manifest["inputs"] = {k: {"path": inputs[k].as_posix(), "sha256": sha256(inputs[k])}
                                  for k in ("fields", "messages", "gui_crosschecks", "fields_summary") if inputs[k] is not None}
        run_manifest["stages"].append({"stage": "validate_inputs", "status": "PASS"})
        run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + run_manifest["input_manifest"]["sha256"][:8]
        run_manifest["run_id"] = run_id

        s = output_dir / "stages"
        f, m = str(inputs["fields"]), str(inputs["messages"])
        g3_args = ["--associations", str(s / "g2b" / "associations.json"), "--output-dir", str(s / "g3ab")]
        if inputs["gui_crosschecks"] is not None:
            g3_args[2:2] = ["--gui-crosschecks", str(inputs["gui_crosschecks"])]
        common_report = ["--findings", str(output_dir / "findings.json"), "--trace-file-name", trace["file_name"],
                         "--trace-sha256", trace["sha256"].upper(), "--tlp-count", str(trace["tlp_count"])]
        plan = [
            ("g2b", g2b_associate.main, ["--fields", f, "--output-dir", str(s / "g2b")], [s / "g2b" / "roles.json", s / "g2b" / "associations.json"]),
            ("g3ab", g3_candidates.main, g3_args, [s / "g3ab" / "candidates.json"]),
            ("g3c", g3c_nearby_messages.main, ["--candidates", str(s / "g3ab" / "candidates.json"), "--fields", f, "--messages", m,
                                               "--window", str(PARAMETERS["g3c_window_tlp_rows"]), "--max-packet-gap", str(PARAMETERS["g3c_max_packet_gap"]),
                                               "--output-dir", str(s / "g3c")], [s / "g3c" / "nearby_messages.json"]),
            ("g3d", g3d_context.main, ["--fields", f, "--roles", str(s / "g2b" / "roles.json"), "--associations", str(s / "g2b" / "associations.json"),
                                       "--candidates", str(s / "g3ab" / "candidates.json"), "--nearby", str(s / "g3c" / "nearby_messages.json"),
                                       "--context-rows", str(PARAMETERS["g3d_context_rows"]), "--output-dir", str(s / "g3d")], [s / "g3d" / "contexts.json"]),
            ("g3e", g3e_groups.main, ["--candidates", str(s / "g3ab" / "candidates.json"), "--associations", str(s / "g2b" / "associations.json"),
                                      "--nearby", str(s / "g3c" / "nearby_messages.json"), "--protected-outputs", str(s / "g2b" / "associations.json"),
                                      str(s / "g3ab" / "candidates.json"), str(s / "g3c" / "nearby_messages.json"), str(s / "g3d" / "contexts.json"),
                                      "--output-dir", str(s / "g3e")], [s / "g3e" / "groups.json"]),
            ("g3f", g3f_findings.main, ["--groups", str(s / "g3e" / "groups.json"), "--candidates", str(s / "g3ab" / "candidates.json"),
                                        "--nearby", str(s / "g3c" / "nearby_messages.json"), "--contexts", str(s / "g3d" / "contexts.json"),
                                        "--fields", f, "--output-dir", str(s / "g3f")], [s / "g3f" / "findings.json"]),
        ]
        for name, func, argv, expected in plan:
            run_manifest["stages"].append(run_stage(name, func, argv, expected))
        (output_dir / "findings.json").write_bytes((s / "g3f" / "findings.json").read_bytes())
        run_manifest["stages"].append(run_stage("g7", g7_render_markdown.main, common_report + ["--output", str(output_dir / "report.md")], [output_dir / "report.md"]))
        run_manifest["stages"].append(run_stage("g8", g8_render_html.main, common_report + ["--output", str(output_dir / "report.html")], [output_dir / "report.html"]))

        findings_total = len(json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))["findings"])
        readme = README_TEMPLATE.format(run_id=run_id, trace_name=trace["file_name"], trace_sha=trace["sha256"].upper(), findings=findings_total)
        (output_dir / "使用說明.md").write_text(readme, encoding="utf-8", newline="\n")
        run_manifest["package"] = {name: sha256(output_dir / name) for name in ("report.html", "report.md", "findings.json", "使用說明.md")}
        run_manifest["findings_total"] = findings_total
        run_manifest["status"] = "PASS"
    except TriageError as exc:
        run_manifest["failed_stage"] = exc.stage
        run_manifest["error"] = str(exc)
        raise
    finally:
        run_manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (output_dir / "run-manifest.json").write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Base for relative input paths")
    args = parser.parse_args(argv)
    try:
        result = run(args.input_manifest, args.output_dir, args.repo_root)
    except (TriageError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        stage = getattr(exc, "stage", "validate_inputs")
        print(f"PCIe triage not produced (stage {stage}): {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "run_id": result["run_id"], "findings_total": result["findings_total"],
                      "package": result["package"], "output_dir": args.output_dir.as_posix()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
