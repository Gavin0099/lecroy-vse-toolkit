"""Validate an acquired PETracer report and normalize it to a streaming JSONL file."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

FIELDS = {
    "TLP": ("psn", "type", "requester_id", "tag", "bad_crc", "has_errors", "length", "completion_status"),
    "ACK": ("type", "ack_nak_seq_num", "bad_crc", "has_errors", "vc", "header_credit",
            "data_credit", "header_scale", "data_scale"),
    "LINK": ("type", "condition"),
    "LTSSM": ("origin", "state", "substate", "state_valid", "subsubstate"),
    "ORDERED_SET": ("type", "speed_code", "link_width"),
    "EIE": (),
}
FIELDS["NAK"] = FIELDS["DLLP"] = FIELDS["ACK"]
TEXT_FIELDS = {"condition": {"up", "down", "other"}, "origin": {"idle", "packet"}}


def integer(value: str) -> int | None:
    return None if value == "NA" else int(value)


def event_row(parts: list[str], channels: dict[int, str]) -> dict:
    _, kind, index, channel, channel_name, seconds, nanoseconds, picoseconds, payload = parts
    field_names = FIELDS[kind]
    values = payload.split(",") if payload else []
    if len(values) != len(field_names):
        raise ValueError(f"invalid {kind} field count")
    fields = {}
    for name, value in zip(field_names, values, strict=True):
        if name in TEXT_FIELDS:
            if value not in TEXT_FIELDS[name]:
                raise ValueError(f"invalid {name} in {kind}")
            fields[name] = value
        else:
            fields[name] = integer(value)
    if "bad_crc" in fields:
        bad_crc, has_errors = fields["bad_crc"], fields["has_errors"]
        if bad_crc not in (0, 1, None) or has_errors not in (0, 1, None):
            raise ValueError(f"invalid CRC/error flag in {kind}")
        if bad_crc == 1:
            fields["crc_validation"] = "invalid"
        elif bad_crc == 0 and has_errors == 0:
            fields["crc_validation"] = "valid_analyzer_reported"
        else:
            fields["crc_validation"] = "unknown"

    channel_id = int(channel)
    direction = channels.get(channel_id)
    return {
        "kind": kind,
        "packet_index": int(index),
        "channel": channel_id,
        "channel_label": channel_name,
        "direction": direction if channel_name == direction else "UNKNOWN",
        "timestamp": {"seconds": integer(seconds), "nanoseconds": integer(nanoseconds),
                      "picoseconds": integer(picoseconds)},
        "fields": fields,
    }


def receipt_scope(receipt: dict) -> tuple[int, int]:
    if (receipt.get("schema") != "pcie.protocol-events-acquisition/v1"
            or receipt.get("status") != "VSE_DONE" or receipt.get("script_result") != 2
            or receipt.get("inputs_unchanged") is not True or receipt["before"] != receipt["after"]
            or receipt.get("owned_analyzer_pids_remaining") != []):
        raise ValueError("acquisition is incomplete or its integrity could not be established")
    source = receipt["before"]["source"]["sha256"]
    display = receipt["before"]["display"]["sha256"]
    if source != display and not receipt.get("conversion_manifest_sha256"):
        raise ValueError("missing sealed conversion reference")
    first, last = receipt["window"]
    if not 0 <= first <= last < receipt["native_packet_count"]:
        raise ValueError("acquisition window is outside the native packet range")
    return first, last


def normalize(acquisition: Path, output: Path) -> dict:
    receipt = json.loads((acquisition / "acquisition.json").read_text(encoding="utf-8"))
    first, last = receipt_scope(receipt)
    output.mkdir(parents=True, exist_ok=False)
    row_counts: Counter[str] = Counter()
    script_counts = {}
    flags: Counter[str] = Counter()
    directions: dict[str, set[str]] = {}
    observed = set()
    digest = hashlib.sha256()
    previous_index = first
    channels = None
    ignore_errors = None
    finished = False
    stream_file = output / "events.jsonl"

    with (acquisition / "protocol-events.txt").open("rb") as raw, stream_file.open(
            "x", encoding="utf-8", newline="\n") as stream:
        for encoded in raw:
            digest.update(encoded)
            line = encoded.decode("utf-8").rstrip("\r\n")
            if not line.startswith("PCIE_EVENT"):
                continue
            if finished:
                raise ValueError("protocol record after END")
            tag, *parts = line.split("|")
            if tag == "PCIE_EVENT_BEGIN" and channels is None:
                version, lower, upper, upstream, downstream, ignore = parts
                if (int(version), int(lower), int(upper)) != (1, first, last) or int(upstream) == int(downstream):
                    raise ValueError("protocol header does not match the acquisition")
                channels = {int(upstream): "Upstream", int(downstream): "Downstream"}
                ignore_errors = integer(ignore)
            elif tag == "PCIE_EVENT" and channels is not None and not script_counts:
                event = event_row([tag, *parts], channels)
                index, kind = event["packet_index"], event["kind"]
                if not previous_index <= index <= last:
                    raise ValueError("packet index is outside the window or out of order")
                if index != previous_index:
                    observed.clear()
                event_key = (event["channel"], kind, event["fields"].get("origin"))
                if event_key in observed:
                    raise ValueError("duplicate event for the packet and channel")
                observed.add(event_key)
                previous_index = index
                row_counts[kind] += 1
                directions.setdefault(kind, set()).add(event["direction"])
                if "crc_validation" in event["fields"]:
                    flags[event["fields"]["crc_validation"]] += 1
                stream.write(json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n")
            elif tag == "PCIE_EVENT_COUNT" and channels is not None:
                kind, value = parts
                if kind not in FIELDS or kind in script_counts:
                    raise ValueError("unknown or duplicate protocol event count")
                script_counts[kind] = int(value)
            elif tag == "PCIE_EVENT_END" and not parts and channels is not None:
                if script_counts != {kind: row_counts[kind] for kind in FIELDS}:
                    raise ValueError("protocol event counts do not match emitted rows")
                finished = True
            else:
                raise ValueError(f"unexpected protocol record: {tag}")
    if not finished or digest.hexdigest() != receipt["report"]["sha256"]:
        raise ValueError("report footer missing or report SHA-256 mismatch")

    before = receipt["before"]
    with stream_file.open("rb") as stream:
        stream_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    summary = {
        "schema": "pcie.protocol-event-stream/v1",
        "source_trace_sha256": before["source"]["sha256"],
        "display_trace_sha256": before["display"]["sha256"],
        "packet_namespace": receipt["packet_namespace"],
        "conversion_manifest_sha256": receipt.get("conversion_manifest_sha256"),
        "window_inclusive": [first, last],
        "native_packet_count": receipt["native_packet_count"],
        "capture_mode": "UNKNOWN",
        "capture_continuity": "UNKNOWN",
        "filter_status": receipt["filter_status"],
        "physical_link_mapping": "UNKNOWN",
        "initial_data_link_state": "UNKNOWN",
        "ltssm_ignore_error_setting": ignore_errors,
        "event_reduction": {"LTSSM": "state changes", "ORDERED_SET": "selected TS1/TS2/EIEOS/EIOS"},
        "counts": script_counts,
        "directions": {kind: sorted(values) for kind, values in sorted(directions.items())},
        "crc_validation_counts": dict(sorted(flags.items())),
        "report_sha256": digest.hexdigest(),
        "events_sha256": stream_sha256,
    }
    (output / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = normalize(args.acquisition, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"counts": result["counts"], "capture_continuity": result["capture_continuity"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
