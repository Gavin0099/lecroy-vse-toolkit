"""Compose the PCIe model in a supervised subprocess after native cleanup."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from pcie_event_coverage import digest
import pcie_large_io as large
import pcie_model_storage as storage
import pcie_resources as resources


MODEL_NAME = "desktop-model.json"
FLOW_HANDOFF = "pcie.flow-handoff/v1"
FLOW_BUDGET = 64 * large.MIB
FLOW_ATTACHMENTS = {
    "scenarios.json": ("flow_analysis", "scenarios"),
    "items.json": ("flow_items",),
}
BINDING_KEYS = ("analysis_id", "source_trace_sha256", "display_trace_sha256")


def write_model(root, model):
    path = root / MODEL_NAME
    if path.exists():
        raise FileExistsError(path)
    try:
        large.write_json_bounded(path, model)
        return
    except large.ResourceLimit:
        if not model.get("flow_items"):
            raise

    # Keep the existing desktop/export model contract. These attachments belong
    # only to the worker handoff and are hydrated before the controller uses it.
    folder = root / "model-handoff"
    folder.mkdir()
    binding = {key: model[key] for key in BINDING_KEYS}
    handoff = dict(model, flow_analysis=dict(model["flow_analysis"]))
    refs = {}
    remaining = FLOW_BUDGET
    for name, keys in FLOW_ATTACHMENTS.items():
        node = storage.parent(handoff, keys)
        attachment = folder / name
        size = large.write_json_bounded(attachment, dict(binding=binding, rows=node[keys[-1]]), remaining)
        remaining -= size
        refs[name] = dict(bytes=size, sha256=digest(attachment))
        node[keys[-1]] = []
    handoff["worker_handoff"] = dict(schema=FLOW_HANDOFF, refs=refs)
    manifest = folder / MODEL_NAME
    large.write_json_bounded(manifest, handoff)
    path.with_name(path.name + ".partial").unlink()
    manifest.rename(path)


def read_model(root, analysis_id, limit):
    root = root.resolve()
    path = root / MODEL_NAME
    large.check_file(path, limit)
    model = json.loads(path.read_text(encoding="utf-8"))
    if model["analysis_id"] != analysis_id:
        raise ValueError("離線模型不屬於本次分析工作。")
    handoff = model.pop("worker_handoff", None)
    if handoff is None:
        return model
    if handoff["schema"] != FLOW_HANDOFF or set(handoff["refs"]) != set(FLOW_ATTACHMENTS):
        raise ValueError("離線 Flow 交接附件清單不完整。")
    binding = {key: model[key] for key in BINDING_KEYS}
    folder = root / "model-handoff"
    remaining = FLOW_BUDGET
    for name, keys in FLOW_ATTACHMENTS.items():
        attachment = folder / name
        if attachment.resolve(strict=True) != attachment:
            raise ValueError("離線 Flow 交接附件路徑不符。")
        ref = handoff["refs"][name]
        size = ref["bytes"]
        if type(size) is not int or not 0 < size <= remaining:
            raise large.ResourceLimit("離線 Flow 交接附件超過安全上限。")
        with attachment.open("rb") as stream:
            data = stream.read(size + 1)
        if len(data) != size or hashlib.sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("離線 Flow 交接附件大小或雜湊不符。")
        value = json.loads(data)
        if value["binding"] != binding or not isinstance(value["rows"], list):
            raise ValueError("離線 Flow 交接附件不屬於本次分析工作。")
        storage.parent(model, keys)[keys[-1]] = value["rows"]
        remaining -= size
    return model


def compose(root, analysis_id, cancel=None, progress=lambda text: None):
    root = Path(root)
    limits = large.policy()
    started = time.monotonic()
    with (root / "model-worker.log").open("xb") as log, (root / "model-resources.jsonl").open("x") as samples:
        child = subprocess.Popen([sys.executable, __file__, str(root), analysis_id],
                                 stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            while child.poll() is None:
                if cancel is not None and cancel.is_set():
                    raise InterruptedError("已取消離線分析；原生清理已確認，未使用本次結果。")
                sample = resources.sample(child.pid)
                samples.write(json.dumps(dict(seconds=time.monotonic()-started, process=sample)) + "\n")
                samples.flush()
                if sample and sample["private_commit_bytes"] > limits["worker_private_bytes"]:
                    raise large.ResourceLimit("離線分析程序超過記憶體安全上限；擷取證據保留，未產生完成報告。")
                large.check_disk(root)
                if time.monotonic()-started > limits["other_stage_seconds"]:
                    raise large.ResourceLimit("離線分析逾時；原生工作已結束，擷取證據保留。")
                progress("正在組合流程與證據；原生工作已結束。")
                time.sleep(.5)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
        if child.returncode:
            error = root / "model-error.json"
            detail = json.loads(error.read_text(encoding="utf-8"))["error"] if error.exists() else "請查看 model-worker.log"
            raise large.ResourceLimit("離線分析未完成：" + detail)
    model = read_model(root, analysis_id, limits["max_model_bytes"])
    if cancel is not None and cancel.is_set():
        raise InterruptedError("已取消離線分析；原生清理已確認，未使用本次結果。")
    return model


if __name__ == "__main__":
    root = Path(sys.argv[1])
    try:
        import pcie_workspace
        model = pcie_workspace.compose(root, sys.argv[2])
        if (root/'disk-index.json').exists():
            model=storage.pack(model,root)
        write_model(root, model)
    except Exception as exc:
        (root / "model-error.json").write_text(json.dumps(dict(error=str(exc)), ensure_ascii=False), encoding="utf-8")
        raise
