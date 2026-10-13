"""I01: one typed P03 source block composed with unchanged W1–W5 renderers."""
import argparse
import hashlib
import html
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote
import pcie_field_probe as p
import s01_contract as s

FROZEN_HEAD = "f417eecb340f56d09d6e4c0ca0b86f81e2977181"
UNKNOWN_TEXT = "未知，仍需 capture mode、epoch、保留條件與完整起訖證據"
BOUNDARY_TEXT = "原生解碼的抽樣欄位；不判定重播錯誤、credit 耗盡、缺 Completion 或 compliance PASS／FAIL。"


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args): return subprocess.check_output(["git", "-C", str(root), *args])


def frozen_renderer(root):
    root = Path(root).resolve()
    if git(root, "rev-parse", "HEAD").decode().strip() != FROZEN_HEAD or git(root, "status", "--porcelain").strip():
        raise s.ContractError("W1-W5 dependencies require the verified clean frozen checkout")
    scripts = root / "scripts/pcie"
    sys.path.insert(0, str(scripts))
    report = importlib.import_module("b3d_observation_report")
    dependencies = {}
    for name, module in list(sys.modules.items()):
        if name.startswith(("b1", "b2", "b3", "g2")) and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            if path.parent != scripts: raise s.ContractError("mixed-checkout report dependency: " + name)
            relative = path.relative_to(root).as_posix(); raw = path.read_bytes()
            # Git checkout line-ending filters can legitimately produce CRLF.
            # Compare the clean-filtered object identity, also retain disk SHA.
            if git(root, "hash-object", "--path=" + relative, str(path)).strip() != git(root, "rev-parse", FROZEN_HEAD + ":" + relative).strip():
                raise s.ContractError("frozen report dependency differs from pinned blob")
            dependencies[relative] = hashlib.sha256(raw).hexdigest()
    if not {"scripts/pcie/b3a_event_contract.py", "scripts/pcie/b3b_unified_timeline.py", "scripts/pcie/b3d_observation_report.py"} <= set(dependencies):
        raise s.ContractError("report dependency inventory incomplete")
    return report, dependencies


def load_probe(plan_path, run_directory, profile):
    plan = s.read_json(plan_path); directory = Path(run_directory)
    files = {"plan": Path(plan_path), "run": directory / "native/com-run.json",
             "reports": directory / "native/report-lines.json", "observations": directory / "observations.json",
             "before": directory / "before.json", "after": directory / "after.json"}
    before = s.read_json(files["before"]); after = s.read_json(files["after"])
    if before != after or before["working"]["readonly"] is not True:
        raise s.ContractError("P03 protected identity/readonly evidence invalid")
    if before["working"]["sha256"] != plan["trace_sha256"] or before["source"]["sha256"] != plan["trace_sha256"]:
        raise s.ContractError("P03 identity evidence mismatch")
    value = p.assess(s.read_json(files["run"]), s.read_json(files["reports"]), plan, profile)
    if value != s.read_json(files["observations"]):
        raise s.ContractError("P03 observation differs from native source replay; opaque additions rejected")
    return value, {key: {"path": str(path.resolve()), "sha256": digest(path)} for key, path in files.items()}


def build_appendix(probes, capture_sha, sources):
    if set(probes) != {"dllp", "tlp"}: raise s.ContractError("P03 profiles required")
    for value in probes.values():
        if value["trace_sha256"].lower() != capture_sha.lower(): raise s.ContractError("base and probe capture identity differ")
    # These are independently typed fields, never W1 extensions/details/verdicts.
    return {"schema": "pcie.protocol-appendix/v1", "slice": "P03", "capture_sha256": capture_sha.lower(),
            "origin": "vendor_decoded", "interpretation": "observed_raw_values_only", "qualification": "NOT_EVALUATED",
            "index_namespace": "converted_trace_packet_zero_based", "conversion_index_equivalence": "unknown",
            "source_ids": ["LC-01", "LC-07", "LC-15"], "sources": sources,
            "coverage": dict(probes["dllp"]["coverage"]),
            "question": "此 trace 實際能取得哪些 ACK／NAK、credit 與 TLP 欄位？",
            "missing_evidence": ["適用版本的 replay／credit 規範正文", "連續的雙向 capture、mode 與 epoch",
                                 "原生 group 的逐包引用及唯一 request 身分", "特殊／error／非零 scale 的適用樣本"],
            "profiles": probes}


def bind_authorities(model):
    register = Path(__file__).resolve().parents[1] / "docs/pcie-usb-source-register-20261013.json"
    catalog = s.read_json(register)
    authorities = []
    for source_id in model["source_ids"]:
        source = next(row for row in catalog["sources"] if row["id"] == source_id)
        path = Path(source["local_path"])
        if digest(path) != source["sha256"].lower(): raise s.ContractError("document/source revision drift")
        authorities.append({"source_id": source_id, "revision": source["version"], "sha256": source["sha256"].lower(),
                            "sections": ["5.2.2", "5.2.3"] if source_id == "LC-01" else source.get("sections", [source.get("reference")])})
    model["authorities"] = authorities
    model["authority_register"] = {"path": str(register), "sha256": digest(register)}


def link(source, pointer, output):
    try:
        relative = Path(os.path.relpath(source["path"], output)).as_posix()
        url = quote(relative, safe="/")
    except ValueError:  # Different Windows drives; a local file URI is offline.
        url = Path(source["path"]).resolve().as_uri()
    return url + "#" + quote(pointer, safe="")


def row_text(row):
    cells = []
    for field, cell in row["fields"].items():
        value = str(cell["value"]) if cell["state"] == "available" else ("不適用" if cell["state"] == "not_applicable" else "未知（API 空值）")
        cells.append(field + "=" + value)
    return "; ".join(cells)


def render_block(model, output):
    # Both formats consume the same typed model; source prose is never evaluated.
    lines = ["", "## 新增的 PCIe 原生欄位觀測（P03）", "", model["question"], "", BOUNDARY_TEXT, "",
             "觀測覆蓋：" + UNKNOWN_TEXT, "", "Capture SHA-256: " + model["capture_sha256"], "",
             "欄位值由 LeCroy 解碼。Length、scale 均保留原編碼；時間欄位精度尚未驗證。", ""]
    parts = ['<section id="p03-native-fields"><h2>新增的 PCIe 原生欄位觀測（P03）</h2>',
             '<p>' + html.escape(model["question"]) + '</p>', '<p>' + html.escape(BOUNDARY_TEXT) + '</p>',
             '<p>觀測覆蓋：' + html.escape(UNKNOWN_TEXT) + '</p>', '<p>Capture SHA-256: <code>' + model["capture_sha256"] + '</code></p>',
             '<p>欄位值由 LeCroy 解碼。Length、scale 均保留原編碼；時間欄位精度尚未驗證。</p>']
    target = link(model["authority_register"], "/sources", output)
    lines += ["[規格／API 來源登錄]({})".format(target), ""]
    parts += ['<p><a href="' + html.escape(target, quote=True) + '">規格／API 來源登錄</a></p>']
    for profile, value in model["profiles"].items():
        lines += ["### " + profile.upper(), "", "| 原生型別 | callback 數 | 抽樣筆數 | 觀測 |", "| --- | ---: | ---: | --- |"]
        parts += ['<h3>' + profile.upper() + '</h3><div class="scroll"><table><thead><tr><th>原生型別</th><th>callback 數</th><th>抽樣筆數</th><th>觀測</th></tr></thead><tbody>']
        for count in value["counts"].values():
            state = "已觀測" if count["observation"] == "observed" else "未知（抽樣沒有記錄）"
            lines.append(f'| {count["label"]} | {count["visited"]} | {count["sampled"]} | {state} |')
            parts.append(f'<tr><td>{html.escape(count["label"])}</td><td>{count["visited"]}</td><td>{count["sampled"]}</td><td>{state}</td></tr>')
        lines += ["", "| Packet | channel 原值 | 時間原值 [sec, ns, ps] | 原生型別 | raw fields | 來源 |", "| ---: | ---: | --- | ---: | --- | --- |"]
        parts += ['</tbody></table></div><div class="scroll"><table><thead><tr><th>Packet</th><th>channel 原值</th><th>時間原值 [sec, ns, ps]</th><th>原生型別</th><th>raw fields</th><th>來源</th></tr></thead><tbody>']
        for i, row in enumerate(value["rows"]):
            text = row_text(row); target = link(model["sources"][profile]["observations"], "/rows/" + str(i), output)
            lines.append(f'| {row["index"]} | {row["channel"]} | {row["time2"]} | {row["native_type"]} | {text} | [原生來源]({target}) |')
            parts.append(f'<tr id="p03-{profile}-{row["index"]}"><td>{row["index"]}</td><td>{row["channel"]}</td><td>{row["time2"]}</td><td>{row["native_type"]}</td><td>{html.escape(text)}</td><td><a href="{html.escape(target, quote=True)}">原生來源</a></td></tr>')
        lines.append(""); parts.append('</tbody></table></div>')
    lines += ["### 還缺哪些證據", ""] + ["- " + text for text in model["missing_evidence"]]
    parts += ['<h3>還缺哪些證據</h3><ul>'] + ['<li>' + html.escape(text) + '</li>' for text in model["missing_evidence"]] + ['</ul></section>']
    return "\n".join(lines) + "\n", "\n".join(parts)


def compose(base_md, base_html, appendix, output):
    md, section = render_block(appendix, output)
    if base_html.count("</main>") != 1: raise s.ContractError("unsupported frozen renderer boundary")
    return base_md + md, base_html.replace("</main>", section + "</main>")


def generate(frozen_root, timeline, plan, dllp_run, tlp_run, output):
    frozen_root = Path(frozen_root).resolve(); output = Path(output).resolve()
    if output.exists() or output.is_relative_to(frozen_root): raise s.ContractError("fresh output outside frozen checkout required")
    if output.drive.lower() != frozen_root.drive.lower():
        raise s.ContractError("output must share the frozen checkout drive to preserve existing W5 relative links")
    report, dependencies = frozen_renderer(frozen_root)
    doc = report.adapter.verified_timeline(Path(timeline), frozen_root)
    base = report.build_model(doc, frozen_root)
    probes = {}; sources = {}
    for profile, directory in [("dllp", dllp_run), ("tlp", tlp_run)]:
        probes[profile], sources[profile] = load_probe(plan, directory, profile)
    appendix = build_appendix(probes, base["capture_sha256"], sources)
    bind_authorities(appendix)
    prefix = Path(os.path.relpath(frozen_root, output)).as_posix()
    base_md = report.render_markdown(base, prefix); base_html = report.render_html(base, prefix)
    markdown, webpage = compose(base_md, base_html, appendix, output)
    provenance = {"frozen_commit": FROZEN_HEAD, "frozen_checkout": str(frozen_root), "dependencies": dependencies,
                  "timeline": {"path": str(Path(timeline).resolve()), "sha256": digest(timeline)},
                  "base_markdown_sha256": hashlib.sha256(base_md.encode()).hexdigest(),
                  "base_html_sha256": hashlib.sha256(base_html.encode()).hexdigest()}
    # Detect source drift between validation/rendering and publication of outputs.
    for group in sources.values():
        if any(digest(v["path"]) != v["sha256"] for v in group.values()): raise s.ContractError("P03 source changed during render")
    if digest(appendix["authority_register"]["path"]) != appendix["authority_register"]["sha256"]:
        raise s.ContractError("authority register changed during render")
    if frozen_renderer(frozen_root)[1] != dependencies: raise s.ContractError("frozen dependency drift")
    output.mkdir(parents=True)
    for name, value in [("report.md", markdown), ("report.html", webpage),
                        ("report.json", json.dumps({"schema": "pcie.composed-report/v1", "base_report": base,
                          "protocol_appendix": appendix, "provenance": provenance}, ensure_ascii=False, indent=2) + "\n")]:
        (output / name).write_text(value, encoding="utf-8", newline="\n")
    return {"status": "LOCAL_SOURCE_BLOCK_COMPLETE", "rows": sum(len(v["rows"]) for v in probes.values()), "frozen_commit": FROZEN_HEAD}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["frozen-root", "timeline", "plan", "dllp-run", "tlp-run", "output"]: parser.add_argument("--" + arg, required=True, type=Path)
    a = parser.parse_args()
    try:
        print(json.dumps(generate(a.frozen_root, a.timeline, a.plan, a.dllp_run, a.tlp_run, a.output))); return 0
    except (s.ContractError, ValueError, OSError, KeyError) as e:
        print(json.dumps({"status": "INVALID", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
