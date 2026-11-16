#!/usr/bin/env python3
"""Check a saved PCIe-G1a count-only VSE output log and print its bounded result as JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


HEADER = "PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none"
PROGRESS_EVERY = 250_000
DONE_MARKER = "------- D O N E !!! -------"
PROGRESS_RE = re.compile(r"^PCIE_G1A_PROGRESS\|(?P<count>\d+)\|(?P<index>\d+)$")
SUMMARY_RE = re.compile(
    r"^PCIE_G1A_SUMMARY\|tlp_count=(?P<count>\d+)\|first_index=(?P<first_index>\d+)\|"
    r"first_time=(?P<first_time>[^|]*)\|last_index=(?P<last_index>\d+)$"
)
RUNTIME_ERROR_RE = re.compile(
    r"No channels found to be sent|No events found to be sent|runtime error|script error",
    re.IGNORECASE,
)


class G1aLogError(ValueError):
    """The log does not establish a complete count-only traversal."""


def check_log(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines()]
    if lines.count(HEADER) != 1:
        raise G1aLogError("Expected exactly one G1a header")
    if lines.count(DONE_MARKER) != 1:
        raise G1aLogError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise G1aLogError("The log contains a runtime-error marker")

    progress: list[tuple[int, int]] = []
    summaries: list[re.Match[str]] = []
    for line in lines:
        if not line.startswith("PCIE_G1A_") or line == HEADER:
            continue
        if match := PROGRESS_RE.fullmatch(line):
            progress.append((int(match["count"]), int(match["index"])))
        elif match := SUMMARY_RE.fullmatch(line):
            summaries.append(match)
        else:
            raise G1aLogError(f"Unrecognized G1a line: {line}")
    if len(summaries) != 1:
        raise G1aLogError("Expected exactly one finish summary; traversal end is not established")

    for position, (count, _) in enumerate(progress, start=1):
        if count != position * PROGRESS_EVERY:
            raise G1aLogError(f"Progress marker {position} has count {count}")
    indices = [index for _, index in progress]
    if any(later <= earlier for earlier, later in zip(indices, indices[1:])):
        raise G1aLogError("Progress packet indices are not strictly increasing")

    summary = summaries[0]
    count = int(summary["count"])
    first_index = int(summary["first_index"])
    last_index = int(summary["last_index"])
    first_time = summary["first_time"].strip()
    if count == 0:
        if progress or first_index or last_index or first_time:
            raise G1aLogError("Zero-TLP summary carries TLP positions")
    else:
        if not first_time:
            raise G1aLogError("Summary lacks the first TLP display time")
        if first_index > last_index:
            raise G1aLogError("First TLP index is after the last TLP index")
        if progress and (count < progress[-1][0] or last_index < progress[-1][1]):
            raise G1aLogError("Summary is behind the last progress marker")
        if len(progress) != count // PROGRESS_EVERY:
            raise G1aLogError("Progress marker count does not match the summary count")

    return {
        "status": "PASS_COUNT_ONLY",
        "tlp_callback_count": count,
        "first_tlp_index": first_index if count else None,
        "first_tlp_time_display": first_time or None,
        "last_tlp_index": last_index if count else None,
        "progress_markers": len(progress),
        "not_established": [
            "total event count (vendor index is an identifier, not a count)",
            "per-row fields or row export",
            "reproducibility (G1d)",
            "wall-clock runtime (recorded separately from GUI observation)",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Saved VSE output log")
    args = parser.parse_args(argv)
    try:
        raw = args.log.read_bytes()
        result = check_log(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, G1aLogError) as exc:
        print(f"G1a log not accepted: {exc}", file=sys.stderr)
        return 2
    result["log_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
