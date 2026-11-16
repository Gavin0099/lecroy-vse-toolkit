"""Associate captured PCIe transactions and decode observed Config register identities."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
import re


_BINDING_FIELDS = (
    "analysis_id", "source_trace_sha256", "display_trace_sha256",
    "packet_namespace", "native_packet_count", "coverage",
)
_READS = {"CfgRd0", "CfgRd1"}
_WRITES = {"CfgWr0", "CfgWr1"}
_CONFIG = _READS | _WRITES
_MEMORY = {"MRd32", "MRd64"}
_COMPLETIONS = {"Cpl", "CplD"}
_FAILURE = {"UR", "CA", "CRS"}
_KINDS = _CONFIG | _MEMORY | _COMPLETIONS | {"OtherNonPosted"}
_REVERSE = {"Upstream": "Downstream", "Downstream": "Upstream"}
_NUMERIC_LIMITS = {
    "time_ns": None, "requester_id": 0xFFFF, "tag": 0x3FF, "device_id": 0xFFFF,
    "register": 0xFFF, "address": 0xFFFFFFFFFFFFFFFF, "length_dw": 1024,
    "first_be": 0xF, "last_be": 0xF, "value": 0xFFFFFFFF, "payload_bytes": 4096,
    "byte_count": 4096, "lower_address": 0x7F,
}
_EVENT_FIELDS = {*_NUMERIC_LIMITS, "packet_index", "time_display", "direction", "kind", "status"}
_METADATA_FIELDS = {"packet_index", "time_display", "direction", "kind", "requester_id", "tag"}
_EXT_HEADERS = {
    0x000B: "VSEC_EXT_CAP_HEADER",
    0x000E: "ARI_EXT_CAP_HEADER",
    0x0018: "LTR_EXT_CAP_HEADER",
    0x001E: "L1SS_EXT_CAP_HEADER",
}
# Standard field positions also appear in Linux include/uapi/linux/pci_regs.h.
_EXT_HEADER_FIELDS = (
    ("Extended Capability ID", 0, 16), ("Capability Version", 16, 4),
    ("Next Extended Capability Offset", 20, 12),
)
_WRITE_FIELDS = {
    **dict.fromkeys(_EXT_HEADERS.values(), _EXT_HEADER_FIELDS),
    "PCI_EXP_CAP_HEADER": (("Capability ID", 0, 8), ("Next Capability Pointer", 8, 8)),
    "VSEC_SECOND_HEADER": (("VSEC ID", 0, 16), ("VSEC Revision", 16, 4), ("VSEC Length", 20, 12)),
    "PCI_EXP_LINK_CONTROL": (("ASPM Control", 0, 2), ("Common Clock Configuration", 6, 1)),
}
_BURST_GAP_NS = 100_000_000


def _check(condition, field):
    if not condition:
        raise ValueError(f"Invalid PCIe Config/UR observations: {field}")


def _is_uint(value, limit=None):
    return type(value) is int and value >= 0 and (limit is None or value <= limit)


def _is_hex(value, size):
    return isinstance(value, str) and len(value) == size and re.fullmatch("[a-f0-9]+", value)


def _event(raw, count):
    _check(isinstance(raw, dict) and raw.keys() == _EVENT_FIELDS | {"evidence"}, "event fields")
    for field, limit in _NUMERIC_LIMITS.items():
        value = raw[field]
        _check(value is None or _is_uint(value, limit), field)
    _check(_is_uint(raw["packet_index"], count - 1), "event packet_index")
    _check(isinstance(raw["time_display"], str), "time_display")
    _check(isinstance(raw["kind"], str) and raw["kind"] in _KINDS, "kind")
    _check(raw["direction"] in ("Upstream", "Downstream", "UNKNOWN"), "direction")
    _check(raw["status"] in ("SC", "UR", "CA", "CRS", "UNKNOWN", None), "status")
    _check(isinstance(raw["evidence"], list) and raw["evidence"], "event evidence")
    supported = set()
    for ref in raw["evidence"]:
        _check(
            isinstance(ref, dict) and ref.keys() == {"kind", "file", "sha256", "line", "fields"},
            "reference fields",
        )
        kind, file, fields = ref["kind"], ref["file"], ref["fields"]
        _check(kind in ("RAW_FRAME_VERIFIED", "NATIVE_TEXT_VERIFIED", "METADATA_ONLY"), "reference kind")
        _check(
            isinstance(file, str) and ":" not in file
            and all(part not in ("", ".", "..") for part in file.replace("\\", "/").split("/"))
            and not any(ord(character) < 32 for character in file),
            "reference file",
        )
        _check(_is_hex(ref["sha256"], 64) and _is_uint(ref["line"]) and ref["line"] > 0, "reference locator")
        _check(
            isinstance(fields, list) and fields
            and all(isinstance(field, str) and field in _EVENT_FIELDS for field in fields)
            and len(set(fields)) == len(fields),
            "reference field provenance",
        )
        supported.update(set(fields) & _METADATA_FIELDS if kind == "METADATA_ONLY" else fields)
    _check({"packet_index", "kind"} <= supported, "packet and kind provenance")
    defaults = {"direction": "UNKNOWN", "time_display": ""}
    return {key: value if key in supported or key == "evidence" else defaults.get(key)
            for key, value in raw.items()}


def _validated(observations):
    _check(isinstance(observations, dict) and observations.get("schema") == "pcie.config-ur-observations/v1",
           "schema")
    for field in ("analysis_id", "source_trace_sha256", "display_trace_sha256"):
        _check(_is_hex(observations.get(field), 32 if field == "analysis_id" else 64), field)
    _check(observations.get("packet_namespace") in (
        "native_trace_packet_zero_based", "converted_trace_packet_zero_based",
    ), "packet_namespace")
    count, coverage = observations.get("native_packet_count"), observations.get("coverage")
    _check(_is_uint(count) and isinstance(coverage, dict), "native_packet_count or coverage")
    _check(all(type(coverage.get(field)) is bool for field in ("stream_complete", "link_boundaries_complete"))
           and coverage.get("full_trace_coverage") == "UNKNOWN"
           and all(_is_uint(coverage.get(field)) for field in ("unsupported_frame_rows", "omitted_rows")),
           "coverage fields")
    cuts, raw_events = observations.get("link_downs"), observations.get("events")
    _check(isinstance(cuts, list) and all(_is_uint(cut, count - 1) for cut in cuts)
           and all(before < after for before, after in zip(cuts, cuts[1:])), "ordered link_downs")
    _check(isinstance(raw_events, list), "events")
    events = [_event(raw, count) for raw in raw_events]
    packets = [event["packet_index"] for event in events]
    _check(all(before < after for before, after in zip(packets, packets[1:])), "ordered event packets")
    _check(not set(cuts).intersection(packets), "link_downs overlap event packets")
    return coverage, cuts, events


def _key(event):
    direction = event["direction"]
    if event["kind"] in _COMPLETIONS:
        direction = _REVERSE.get(direction)
    if direction in _REVERSE and event["requester_id"] is not None and event["tag"] is not None:
        return event["requester_id"], event["tag"], direction
    return None


def _new_row(request, epoch, status):
    config = request["kind"] in _CONFIG
    return {
        "id": f"p{request['packet_index']}", "epoch": epoch, "request": request,
        "completion": None, "completion_status": status,
        "register": {"identity": "UNKNOWN", "evidence_packets": [], "scope": "unknown"} if config else None,
        "readback": None, "write_effect": "NOT_ESTABLISHED" if request["kind"] in _WRITES else None,
        "bar": None if config else "BAR_UNKNOWN",
    }


@dataclass
class _Pending:
    request: dict
    row: dict | None
    blocked: bool = False
    completed_bytes: int = 0
    completer: int | None = None

    def block(self, status):
        self.blocked = True
        if self.row is not None and self.row["completion_status"] != "AMBIGUOUS":
            self.row["completion_status"] = status


def _memory_range(request):
    base, length = request["address"], request["length_dw"]
    first, last = request["first_be"], request["last_be"]
    if (base is None or base % 4 or not length or not first or last is None
            or (length == 1 and last != 0) or (length > 1 and last == 0)
            or (request["kind"] == "MRd32" and base > 0xFFFFFFFF)
            or base % 4096 + length * 4 > 4096):
        return None
    # Discontinuous enables are not an exact contiguous byte range.
    if length > 1 and (first not in (0x8, 0xC, 0xE, 0xF) or last not in (0x1, 0x3, 0x7, 0xF)):
        return None
    start = (first & -first).bit_length() - 1
    stop = (length - 1) * 4 + (last or first).bit_length()
    if length == 1 and first != ((1 << (stop - start)) - 1) << start:
        return None
    return base + start, stop - start


def _completion_progress(pending, completion):
    """Return True for terminal proof, False for a verified fragment, or None for a gap."""
    request = pending.request
    kind, status = request["kind"], completion["status"]
    if completion["device_id"] is None:
        return None
    length, payload = completion["length_dw"], completion["payload_bytes"]
    no_data = completion["kind"] == "Cpl" and payload == 0 and length in (None, 0)
    if status in _FAILURE:
        return True if no_data and (status != "CRS" or kind in _CONFIG) else None
    if status != "SC":
        return None
    if kind in _WRITES:
        return True if no_data else None
    if completion["kind"] != "CplD" or not length or not payload or payload > length * 4:
        return None
    if kind in _READS:
        shape = length, payload, completion["byte_count"], completion["lower_address"]
        return True if shape == (1, 4, 4, 0) else None
    if kind not in _MEMORY:
        return None
    address_range = _memory_range(request)
    if address_range is None:
        return None
    base, size = address_range
    # Limit successful split accounting to aligned whole-DWORD transfers.
    # Partial BE may need padding interpretation and is kept unresolved.
    if base % 4 or size % 4 or payload != length * 4:
        return None
    remaining = size - pending.completed_bytes
    start = base + pending.completed_bytes
    if (completion["byte_count"] != remaining or payload > remaining
            or completion["lower_address"] != start & 0x7F):
        return None
    # A non-final fragment ends on a 64- or 128-byte Read Completion Boundary.
    # A 64-byte multiple is necessary at either setting.
    if payload < remaining and (start + payload) % 64:
        return None
    pending.completed_bytes += payload
    pending.completer = completion["device_id"]
    return payload == remaining


def _associate(events, cuts, complete):
    intervals = defaultdict(list)
    for event in events:
        intervals[bisect_right(cuts, event["packet_index"])].append(event)
    rows, unmatched = [], []
    for epoch, interval in intervals.items():
        keys = [_key(event) for event in interval]
        interval_complete = complete and None not in keys
        initial_status = "DATA_GAP"
        if interval_complete:
            initial_status = "NO_COMPLETION_OBSERVED_BEFORE_LINK_DOWN" if epoch < len(cuts) else "NO_COMPLETION_OBSERVED"
        pending = {}
        for key, event in zip(keys, interval):
            kind = event["kind"]
            if kind not in _COMPLETIONS:
                row = _new_row(event, epoch, initial_status) if kind in _CONFIG else None
                if row is not None:
                    rows.append(row)
                if not interval_complete:
                    continue
                if key in pending:
                    pending[key].block("AMBIGUOUS")
                    if row is not None:
                        row["completion_status"] = "AMBIGUOUS"
                    continue
                pending[key] = _Pending(event, row)
                continue
            candidate = pending.get(key)
            abnormal = event["status"] != "SC"
            if candidate is None or candidate.blocked:
                if abnormal:
                    unmatched.append(event)
                continue
            request = candidate.request
            target = request["device_id"] if request["kind"] in _CONFIG else candidate.completer
            if target is not None and event["device_id"] is not None and target != event["device_id"]:
                if abnormal:
                    unmatched.append(event)
                continue
            progress = _completion_progress(candidate, event)
            if request["kind"] in _CONFIG and target is None:
                progress = None
            if progress is None:
                candidate.block("DATA_GAP")
                if abnormal:
                    unmatched.append(event)
                continue
            if not progress:
                continue
            pending.pop(key)
            row = candidate.row
            if request["kind"] in _MEMORY and event["status"] in {"UR", "CA"}:
                row = _new_row(request, epoch, initial_status)
                rows.append(row)
            if row is not None:
                row["completion"] = event
                row["completion_status"] = event["status"]
            elif abnormal:
                unmatched.append(event)
        for candidate in pending.values():
            if candidate.completed_bytes:
                candidate.block("DATA_GAP")
    rows.sort(key=lambda row: row["request"]["packet_index"])
    return rows, unmatched


def _config_address(request):
    offset = request["register"]
    if (request["device_id"] is not None and request["requester_id"] is not None
            and request["direction"] in _REVERSE and offset is not None and offset % 4 == 0
            and request["length_dw"] == 1 and request["last_be"] == 0 and request["first_be"]):
        return (request["direction"], request["requester_id"], request["device_id"]), offset
    return None, None


def _read_value(samples, offset, mask):
    values = samples.get(offset, ())
    if not values:
        return None, ()
    value = values[0][0] & mask
    if any(other & mask != value for other, _ in values):
        return None, ()
    return value, values[0][1]


def _capabilities(samples):
    identities = {}
    pointer, evidence = _read_value(samples, 0x34, 0xFF)
    header_type, _ = _read_value(samples, 0x0C, 0x007F0000)
    visited = set()
    if header_type in (None, 0, 0x00010000):
        while pointer is not None and 0x40 <= pointer <= 0xFC and pointer % 4 == 0 and pointer not in visited:
            visited.add(pointer)
            header, refs = _read_value(samples, pointer, 0xFFFF)
            if header in (None, 0, 0xFFFF):
                break
            capability_id, next_pointer = header & 0xFF, header >> 8
            evidence += refs
            if capability_id == 0x10:
                identities[pointer] = ("PCI_EXP_CAP_HEADER", evidence)
                flags, _ = _read_value(samples, pointer, 0x00FF0000)
                # Root Complex integrated endpoints and event collectors have no Link Control.
                if (flags and (flags >> 20) in (0, 1, 4, 5, 6, 7, 8)
                        and pointer + 0x10 <= 0xFC and (not next_pointer or next_pointer > pointer + 0x10)):
                    identities[pointer + 0x10] = ("PCI_EXP_LINK_CONTROL", evidence)
            pointer = next_pointer

    pointer, evidence, visited = 0x100, (), set()
    while 0x100 <= pointer <= 0xFFC and pointer % 4 == 0 and pointer not in visited:
        visited.add(pointer)
        header, refs = _read_value(samples, pointer, 0xFFFFFFFF)
        if header in (None, 0, 0xFFFFFFFF):
            break
        capability_id, next_pointer = header & 0xFFFF, header >> 20
        evidence += refs
        if capability_id in _EXT_HEADERS:
            identities[pointer] = (_EXT_HEADERS[capability_id], evidence)
        if capability_id == 0x000B and pointer + 4 <= 0xFFC and (not next_pointer or next_pointer > pointer + 4):
            identities[pointer + 4] = ("VSEC_SECOND_HEADER", evidence)
        pointer = next_pointer
    return identities


def _annotate_config(rows):
    samples = defaultdict(lambda: defaultdict(list))
    reads = defaultdict(list)
    for row in rows:
        request, completion = row["request"], row["completion"]
        if request["kind"] not in _READS or row["completion_status"] != "SC" or completion["value"] is None:
            continue
        device, offset = _config_address(request)
        if device is None:
            continue
        reads[device, offset].append(row)
        if request["first_be"] == 0xF:
            refs = (request["packet_index"], completion["packet_index"])
            samples[device, row["epoch"]][offset].append((completion["value"], refs))

    definitions = defaultdict(list)
    for (device, epoch), registers in samples.items():
        for offset, (identity, evidence) in _capabilities(registers).items():
            definitions[device, offset].append((epoch, identity, evidence))

    eligible_reads = {}
    for row in rows:
        request, epoch = row["request"], row["epoch"]
        device, offset = _config_address(request)
        if device is None:
            continue
        choices = definitions.get((device, offset), ())
        match = bisect_left(choices, (epoch,))
        if match < len(choices):
            observed_epoch, identity, evidence = choices[match]
            row["register"] = {
                "identity": identity, "evidence_packets": list(evidence),
                "scope": "same_interval" if observed_epoch == epoch else "later_interval",
            }
        if request["kind"] not in _WRITES:
            continue
        _write_fields(row["register"], request)
        minimum = (row["completion"] or request)["packet_index"]
        enabled = request["first_be"]
        lookup = (device, offset, enabled)
        if lookup not in eligible_reads:
            eligible_reads[lookup] = [
                read for read in reads.get((device, offset), ())
                if read["request"]["first_be"] & enabled == enabled
            ]
        choices = eligible_reads[lookup]
        if row["completion_status"] == "SC":
            match = bisect_right(choices, minimum, key=lambda read: read["request"]["packet_index"])
        else:
            match = bisect_right(choices, epoch, key=lambda read: read["epoch"])
        if match < len(choices):
            read = choices[match]
            row["readback"] = {
                "request": read["request"], "completion": read["completion"],
                "scope": "same_interval" if read["epoch"] == epoch else "later_interval",
            }


def _write_fields(register, request):
    value = request["value"]
    if value is None or request["payload_bytes"] != 4:
        return
    first_be = request["first_be"]
    fields = []
    for name, start, width in _WRITE_FIELDS.get(register["identity"], ()):
        required = ((1 << ((start + width - 1) // 8 + 1)) - 1) ^ ((1 << (start // 8)) - 1)
        if first_be & required == required:
            fields.append({"name": name, "value": (value >> start) & ((1 << width) - 1)})
    if fields:
        register["write_fields"] = fields


def _ur_groups(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["completion_status"] == "UR" and row["bar"] == "BAR_UNKNOWN":
            address_range = _memory_range(row["request"])
            if address_range is not None:
                groups[address_range].append(row)
    result = []
    for (address, size), members in sorted(groups.items()):
        bursts = []
        last_time = last_epoch = None
        for row in members:
            time, epoch = row["request"]["time_ns"], row["epoch"]
            if (last_time is None or time is None or epoch != last_epoch
                    or not 0 <= time - last_time <= _BURST_GAP_NS):
                bursts.append({"start_ns": time, "end_ns": time, "count": 0, "row_ids": []})
            bursts[-1]["end_ns"] = time
            bursts[-1]["count"] += 1
            bursts[-1]["row_ids"].append(row["id"])
            last_time, last_epoch = time, epoch
        result.append({
            "address": address, "byte_length": size, "count": len(members),
            "row_ids": [row["id"] for row in members], "bursts": bursts,
        })
    return result


def analyze(observations):
    """Produce evidence from one validated source-bound native observation stream."""
    coverage, cuts, events = _validated(observations)
    complete = coverage["stream_complete"] and coverage["link_boundaries_complete"] and not coverage["omitted_rows"]
    rows, unmatched = _associate(events, cuts, complete)
    _annotate_config(rows)
    return {
        "schema": "pcie.config-ur-evidence/v1",
        **{field: observations[field] for field in _BINDING_FIELDS},
        "rows": rows, "ur_groups": _ur_groups(rows), "unmatched_completions": unmatched,
    }
