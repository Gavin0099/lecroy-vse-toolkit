"""Bounded acquisition I/O. Limits are local resource policy, not PCIe rules."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import time

MIB = 1024 * 1024
DEFAULTS = {
    "disk_reserve_bytes": 2 * 1024 * MIB,
    "max_callback_bytes": MIB,
    "max_probe_bytes": 8 * MIB,
    "dense_probe_bytes": 1024 * MIB,
    "max_tlp_rows": 20000,
    "max_model_bytes": 8 * MIB,
    "worker_private_bytes": 512 * MIB,
    "native_private_bytes": 4 * 1024 * MIB,
    "controller_private_bytes": 512 * MIB,
    "total_seconds": 7200,
    "open_seconds": 1200,
    "probe_seconds": 1800,
    "other_stage_seconds": 900,
    "no_progress_warning_seconds": 60,
}


class ResourceLimit(ValueError):
    """Refusal is not a successful capacity test."""


def policy(value=None):
    result = dict(DEFAULTS)
    if value is not None:
        if not isinstance(value, dict) or set(value) - set(result):
            raise ValueError("Unknown large-trace resource policy")
        for key, number in value.items():
            if type(number) is not int or number <= 0:
                raise ValueError("Resource policy must contain positive integers: " + key)
            result[key] = number
    return result


def check_disk(path, required=0, reserve=None):
    path = Path(path).resolve()
    while not path.exists():
        if path.parent == path:
            raise OSError("Cannot inspect output volume")
        path = path.parent
    free = shutil.disk_usage(path).free
    minimum = DEFAULTS["disk_reserve_bytes"] if reserve is None else reserve
    if free < required + minimum:
        raise ResourceLimit(
            f"磁碟可用空間不足：{path.anchor} 剩餘 {free} bytes，"
            f"本階段至少需要 {required + minimum} bytes；未完成分析。")
    return free


def check_file(path, limit=None):
    size = Path(path).stat().st_size
    maximum = DEFAULTS["max_probe_bytes"] if limit is None else limit
    if size > maximum:
        raise ResourceLimit(f"解碼輸出超過目前解析安全上限：{Path(path).name} "
                            f"{size} > {maximum} bytes；證據保留，尚未完成分析。")
    return size


def check_rows(count, limits=None):
    limits = policy(limits)
    if count > limits["max_tlp_rows"]:
        raise ResourceLimit(f"已取得 {count} 筆 TLP，超過目前解析安全上限 "
                            f"{limits['max_tlp_rows']}；需要大量交易解析路線，"
                            "本次未產生完整分析結果。")


def identity(path, cancelled=lambda: False, progress=None):
    path = Path(path).resolve()
    before=path.stat();digest=hashlib.sha256();count=0
    with path.open('rb') as stream:
        while True:
            if cancelled():raise InterruptedError("Cancelled during source verification")
            block=stream.read(MIB)
            if not block:break
            digest.update(block);count+=len(block)
            if progress:progress(count)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError("Source changed during hashing")
    return dict(path=str(path),sha256=digest.hexdigest(),bytes=count,
                mtime_ns=after.st_mtime_ns,readonly=not bool(after.st_mode & 0o222))


def copy_new(source, destination, *, cancelled=lambda: False, limits=None, progress=None):
    """Exclusive bounded copy; incomplete output remains .partial, never the source."""
    limits = policy(limits)
    source, destination = Path(source), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    partial = destination.with_name(destination.name + ".partial")
    before = source.stat()
    check_disk(destination.parent, before.st_size, limits["disk_reserve_bytes"])
    count = 0
    with source.open("rb") as src, partial.open("xb") as dst:
        while True:
            if cancelled():
                raise InterruptedError("Cancelled while copying the working trace")
            block = src.read(MIB)
            if not block:
                break
            check_disk(destination.parent, len(block), limits["disk_reserve_bytes"])
            if dst.write(block) != len(block):
                raise OSError("Short working-copy write")
            count += len(block)
            if progress:
                progress(count)
        dst.flush()
        os.fsync(dst.fileno())
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or count != before.st_size:
        raise ValueError("Source changed while creating working copy")
    # Same-volume rename does not overwrite on Windows; check explicitly elsewhere.
    if destination.exists():
        raise FileExistsError(destination)
    partial.rename(destination)
    return count


class ReportSpool:
    """COM append-compatible sink; bounded buffer, retained errors, atomic completion."""

    def __init__(self, path, limits=None):
        self.path = Path(path)
        self.partial = self.path.with_name(self.path.name + ".partial")
        self.limits = policy(limits)
        self.stream = self.partial.open("xb", buffering=256 * 1024)
        self.bytes = self.lines = 0
        self.records = 0
        self.failed = None
        self.closed = False
        self.disk_credit = 0
        self.disk_checked_at = 0

    def append(self, value):
        # Exceptions from a COM callback can be swallowed by its dispatcher.
        # Retain the first failure and have the worker observe it explicitly.
        if self.failed:
            return
        try:
            value = str(value)
            maximum = self.limits["max_callback_bytes"]
            if len(value) > maximum:
                raise ResourceLimit("單筆 VSE callback 超過安全長度；保留部分輸出。")
            body = value.encode("utf-8")
            if len(body) > maximum:
                raise ResourceLimit("單筆 VSE callback 超過安全 bytes 上限。")
            needed = len(body) + bool(self.lines)
            if self.bytes + needed > self.limits["max_probe_bytes"]:
                raise ResourceLimit("VSE 輸出超過目前解析安全上限；保留部分輸出，未完成分析。")
            # Reserve a bounded write allowance from a fresh free-space sample.
            # Resolving/querying the volume for every 50-byte COM row dominates
            # dense captures. Recheck at least once per MiB or second. Include
            # the buffered bytes so the eventual flush retains the reserve.
            now = time.monotonic()
            if needed > self.disk_credit or now - self.disk_checked_at >= 1:
                self.disk_credit = max(MIB, needed)
                check_disk(self.path.parent, self.disk_credit + 256 * 1024,
                           self.limits["disk_reserve_bytes"])
                self.disk_checked_at = now
            if self.lines and self.stream.write(b"\n") != 1:
                raise OSError("Short VSE separator write")
            if self.stream.write(body) != len(body):
                raise OSError("Short VSE callback write")
            self.bytes += needed
            self.lines += 1
            self.records += body.count(b'\n') + 1
            self.disk_credit -= needed
        except Exception as exc:
            self.failed = exc

    def check(self):
        if self.failed:
            raise self.failed

    def flush(self):
        self.check()
        check_disk(self.path.parent, 256 * 1024, self.limits["disk_reserve_bytes"])
        self.stream.flush()

    def finish(self, result):
        self.check()
        if result != 2:
            raise ValueError("Incomplete VSE execution; output remains partial")
        self.flush()
        os.fsync(self.stream.fileno())
        self.close()
        if self.path.exists():
            raise FileExistsError(self.path)
        self.partial.rename(self.path)

    def close(self):
        if not self.closed:
            self.stream.close()
            self.closed = True


def validate_bundle(root, limits=None):
    limits = policy(limits)
    if (Path(root)/'disk-index.json').exists():
        limits['max_probe_bytes']=limits['dense_probe_bytes']
    for path in Path(root).glob("*.txt"):
        check_file(path, limits["max_probe_bytes"])


def stage_deadline(stage, limits):
    if stage in ("create_com", "open_working_copy", "convert_working_copy", "reopen_converted_copy"):
        return limits["open_seconds"]
    if stage and stage.startswith("extract_"):
        return limits["probe_seconds"]
    return limits["other_stage_seconds"]


def write_json_bounded(path, value, limit=None):
    """Stream encoding without constructing a second whole JSON string."""
    path = Path(path)
    limit = DEFAULTS["max_model_bytes"] if limit is None else limit
    partial = path.with_name(path.name + ".partial")
    count = 0
    with partial.open("xb") as stream:
        for chunk in json.JSONEncoder(ensure_ascii=False, separators=(",", ":")).iterencode(value):
            data = chunk.encode("utf-8")
            count += len(data)
            if count > limit:
                raise ResourceLimit("分析模型超過目前安全上限；完整擷取保留，尚未完成分析。")
            stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if path.exists():
        raise FileExistsError(path)
    partial.rename(path)
    return count
