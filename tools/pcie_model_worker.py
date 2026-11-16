"""Isolate legacy whole-model composition after native cleanup is verified."""
import json
from pathlib import Path
import subprocess
import sys
import time

import pcie_large_io as large
import pcie_resources as resources


def compose(root, analysis_id, cancel=None, progress=lambda text: None):
    root = Path(root)
    limits = large.policy()
    destination = root / "desktop-model.json"
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
    large.check_file(destination, limits["max_model_bytes"])
    return json.loads(destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    root = Path(sys.argv[1])
    try:
        import pcie_workspace
        model = pcie_workspace.compose(root, sys.argv[2])
        if (root/'disk-index.json').exists():
            import pcie_model_storage
            model=pcie_model_storage.pack(model,root)
        large.write_json_bounded(root / "desktop-model.json", model)
    except Exception as exc:
        (root / "model-error.json").write_text(json.dumps(dict(error=str(exc)), ensure_ascii=False), encoding="utf-8")
        raise
