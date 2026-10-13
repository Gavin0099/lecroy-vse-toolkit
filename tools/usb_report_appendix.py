"""I02: independently typed U02 LINK_CMD block composed with the existing C5 HTML."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote
import usb_field_probe as u
import s01_contract as s

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = "LINK_CMD 原生欄位抽樣；CRC5 未重新計算，沒有判定 Enumeration／flow-control 成功或故障根因。"


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(path): return {"path": str(Path(path).resolve()), "sha256": digest(path)}


def timeline_path(reference, artifact):
    for path in [ROOT / reference, Path(artifact).parent / reference]:
        if path.is_file(): return path.resolve()
    raise s.ContractError("C5 referenced timeline is missing")


def load_model(c5_path, plan_path, run_directory):
    c5_path = Path(c5_path); directory = Path(run_directory); plan = s.read_json(Path(plan_path))
    u.validate_plan(plan)
    if plan["slice"] != "U02": raise s.ContractError("I02 first integration accepts U02 only")
    observation = u.assess(s.read_json(directory / "result.json"), plan)
    if observation != s.read_json(directory / "observations.json"):
        raise s.ContractError("U02 source replay mismatch/opaque additions")
    before = s.read_json(directory / "before.json"); integrity = s.read_json(directory / "integrity.json")
    if (before["source"]["sha256"] != plan["trace_sha256"] or before["working"]["readonly"] is not True
            or integrity["source_before"] != integrity["source_after"] or integrity["working_before"] != integrity["working_after"]
            or integrity["working_after"]["readonly"] is not True):
        raise s.ContractError("U02 protected identity mismatch")
    baseline = s.read_json(c5_path)
    if baseline.get("status") != "PASS" or baseline.get("trace_integrity_qualified") is not True:
        raise s.ContractError("verified historical C5 input required")
    timelines = {}
    for role in ["pass", "fail"]:
        path = timeline_path(baseline[role + "_timeline"], c5_path); doc = s.read_json(path)
        if (doc["before"] != doc["after"] or doc.get("trace_integrity_unchanged") is not True):
            raise s.ContractError("historical timeline identity not qualified")
        timelines[role] = source(path)
        if role == "fail" and doc["before"]["sha256"].lower() != plan["trace_sha256"]:
            raise s.ContractError("C5 fail trace and U02 source are different")
    inputs = {"c5": source(c5_path), "plan": source(plan_path), "renderer": source(ROOT / "tools/render-c5-html.ps1")}
    inputs.update({key: source(directory / (key + ".json")) for key in ["result", "observations", "before", "integrity"]})
    register = ROOT / "docs/pcie-usb-source-register-20261013.json"; inputs["source_register"] = source(register)
    catalog = s.read_json(register); authorities = []
    for sid in ["LC-04", "LC-09", "USB-01"]:
        doc = next(r for r in catalog["sources"] if r["id"] == sid)
        authorities.append({"source_id": sid, "revision": doc["version"], "review_depth": doc["review_depth"],
                            "sha256": doc.get("sha256"), "locator": doc.get("local_path", doc.get("url"))})
    block = {"schema": "usb.native-command-appendix/v1", "slice": "U02", "trace_sha256": plan["trace_sha256"],
             "origin": "vendor_decoded", "qualification": "NOT_EVALUATED", "software_version": before["toolchain"]["software_version"],
             "authorities": authorities, "sources": inputs, "observation": observation,
             "coverage": {"selection": "LINK_CMD; SS/SSP guard; native bad_crc flag1", "sample": "first128 matching callbacks",
                          "retention": "unknown", "extraction": "partial", "filters": "unknown", "capture_mode": "unknown", "epoch": "unknown"},
             "question": "此 trace 有哪些可回查原始 packet 的 LINK_CMD 欄位？",
             "missing_evidence": ["其他 command type／SS mode 的適用樣本", "原生 transaction／transfer 的逐包引用",
                                  "完整 capture、filter、epoch 與 Enumeration 所需事件", "CRC polynomial 與獨立正負樣本"]}
    return {"schema": "usb.composed-report/v1", "historical_c5": baseline, "native_command_observations": block,
            "historical_timelines": timelines}


def href(source_record, pointer, output):
    # USB outputs and evidence share E: in the current validated use case.
    try: url = quote(Path(os.path.relpath(source_record["path"], output)).as_posix(), safe="/")
    except ValueError: url = Path(source_record["path"]).resolve().as_uri()
    return url + "#" + quote(pointer, safe="")


def render_block(block, output):
    obs = block["observation"]
    parts = ['<section id="u02-native-command-fields"><h2>新增的 USB LINK_CMD 原生觀測</h2>',
             '<p>' + html.escape(block["question"]) + '</p>', '<p>' + html.escape(BOUNDARY) + '</p>',
             f'<p>已抽樣 {obs["exported_count"]} 筆，共收到 {obs["callback_count"]} 個 LINK_CMD callbacks。抽樣未覆蓋完整 trace。</p>',
             '<p>Capture mode／epoch／filter／保留條件未知。SS／SSP 是該事件的原生 speed 標籤。</p>',
             '<p>來源 SHA-256 <code>' + block["trace_sha256"] + '</code>；USB Suite ' + html.escape(block["software_version"]) + '</p>',
             '<p><a href="' + html.escape(href(block["sources"]["source_register"], "/sources", output), quote=True) + '">規格／API 來源登錄</a></p>',
             '<div class="raw-table"><table><thead><tr><th>Packet</th><th>time [sec.ns]</th><th>channel 原值</th><th>native mode</th><th>原生 command 名稱／編碼</th><th>Info／CRC5</th><th>replica Info／CRC5</th><th>來源</th></tr></thead><tbody>']
    for i, row in enumerate(obs["records"]):
        url = href(block["sources"]["observations"], "/records/" + str(i), output)
        name = html.escape(row["name_vendor"])
        parts.append(f'<tr id="u02-packet-{row["index"]}"><td>{row["index"]}</td><td>{row["time_sec"]}.{row["time_ns"]:09d}</td><td>{row["channel_raw"]}</td><td>{row["mode_observed"]}</td><td>{name} / {row["lnkcmd_raw"]}</td><td>{row["info_raw"]} / {row["crc5_raw"]}</td><td>{row["replica_info_raw"]} / {row["replica_crc5_raw"]}</td><td><a href="{html.escape(url, quote=True)}">原生來源</a></td></tr>')
    parts += ['</tbody></table></div><h3>還缺哪些證據</h3><ul>']
    parts += ['<li>' + html.escape(value) + '</li>' for value in block["missing_evidence"]]
    return "\n".join(parts + ['</ul></section>'])


def compose(base_html, block, output):
    if base_html.count("</main>") != 1: raise s.ContractError("unsupported C5 renderer boundary")
    return base_html.replace("</main>", render_block(block, output) + "</main>")


def generate(c5, plan, run_directory, output):
    output = Path(output)
    if output.exists(): raise s.ContractError("fresh output required")
    model = load_model(c5, plan, run_directory)
    inputs = model["native_command_observations"]["sources"]; watched = list(inputs.values()) + list(model["historical_timelines"].values())
    output.mkdir(parents=True)
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", inputs["renderer"]["path"],
               "-InputPath", str(Path(c5).resolve()), "-OutputPath", str((output / "historical-c5.html").resolve())]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (output / "renderer.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    if run.returncode: raise s.ContractError("C5 renderer failed; see preserved log")
    base_path = output / "historical-c5.html"
    webpage = compose(base_path.read_text(encoding="utf-8-sig"), model["native_command_observations"], output)
    if any(digest(row["path"]) != row["sha256"] for row in watched): raise s.ContractError("source changed during render")
    model["historical_render_sha256"] = digest(base_path)
    (output / "report.html").write_text(webpage, encoding="utf-8", newline="\n")
    (output / "report.json").write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "LOCAL_USB_SOURCE_BLOCK_COMPLETE", "rows": model["native_command_observations"]["observation"]["exported_count"], "historical_c5_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["c5", "plan", "run-directory", "output"]: parser.add_argument("--" + arg, required=True, type=Path)
    a = parser.parse_args()
    try: print(json.dumps(generate(a.c5, a.plan, a.run_directory, a.output))); return 0
    except (s.ContractError, ValueError, OSError, KeyError) as e:
        print(json.dumps({"status": "INVALID", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
