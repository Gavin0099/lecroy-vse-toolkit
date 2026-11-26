"""Reuse only sealed format conversions; never reuse analysis or display filters."""
import hashlib
import json
import os
from pathlib import Path
import uuid

import pcie_large_io as large

FORMAT = "pcie.converted-copy/v1"
QUOTA = 6 * 1024**3


def key_for(source, native):
    value = dict(schema=FORMAT, source_sha256=source["sha256"],
                 native_version=native["file_version"],
                 executable_sha256=large.identity(native["executable"])["sha256"],
                 typelib_sha256=native["typelib_sha256"], method="OpenFile2", backup=False)
    key = hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return key,value


def lookup(root, key, binding):
    folder=Path(root)/key
    try:
        manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        if manifest.get("binding")!=binding or manifest.get("status")!="SEALED_CONVERSION":
            return None,"metadata_mismatch"
        if manifest.get("cleanup_confirmed") is not True:return None,"cleanup_unknown"
        info=large.identity(folder/"converted.pex")
        if info["sha256"]!=manifest["display_sha256"] or info["bytes"]!=manifest["bytes"] or not info["readonly"]:
            return None,"content_mismatch"
        return info,"verified_converted_copy_only"
    except (OSError,ValueError,KeyError):
        return None,"missing_or_invalid"


def store(root, key, binding, work, receipt, cancelled=lambda:False):
    if cancelled():raise InterruptedError("Cancelled before conversion cache publication")
    conversion=receipt.get("conversion",{})
    if (receipt.get("status")!="ANALYSIS_COMPLETE" or receipt.get("cleanup_status")!="confirmed"
        or conversion.get("status")!="converted" or not conversion.get("close",{}).get("ok")
        or not all(receipt.get(k) is True for k in ("inputs_unchanged","working_unchanged","scripts_unchanged"))):
        return "not_eligible"
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    if (root/key).exists():return "already_present"
    size=Path(work).stat().st_size
    # No automatic eviction: an existing item might be in active use.
    if sum(p.stat().st_size for p in root.rglob("*") if p.is_file())+size>QUOTA:
        return "quota_no_write"
    folder=root/("pending-"+uuid.uuid4().hex);folder.mkdir()
    large.copy_new(work,folder/"converted.pex",cancelled=cancelled)
    (folder/"converted.pex").chmod(0o444)
    info=large.identity(folder/"converted.pex")
    if info["sha256"]!=receipt["working_after"]["sha256"]:
        raise ValueError("Conversion cache copy differs from sealed display")
    manifest=dict(binding=binding,status="SEALED_CONVERSION",display_sha256=info["sha256"],
                  bytes=info["bytes"],cleanup_confirmed=True,
                  reuse="format_conversion_only; all probes and analysis rerun; no context reused")
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    if cancelled():raise InterruptedError("Cancelled before conversion cache publication")
    try:folder.rename(root/key)
    except FileExistsError:return "concurrent_writer_retained"
    return "stored"
