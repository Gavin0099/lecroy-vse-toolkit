"""Source-bound acquisition coverage, separate from protocol conclusions.

An event counter, retained detail rows and whole-trace coverage are different
quantities. This module never converts DONE or zero callbacks into a PASS.
"""
from pathlib import Path
import hashlib
import uuid


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bound_log(root, name, receipt):
    root = Path(root).resolve(strict=True)
    path = (root / name).resolve(strict=True)
    if not path.is_relative_to(root) or path.name != name:
        raise ValueError('Event evidence must belong to this acquisition directory')
    if digest(path) != receipt['log_sha256']:
        raise ValueError('Event evidence SHA-256 mismatch')
    if receipt.get('finished', {}).get('result') != 2:
        raise ValueError('Event script did not finish DONE')
    return path


def identity(analysis_id, source_sha, display_sha, native_version):
    uuid.UUID(hex=analysis_id)
    for value in (source_sha, display_sha):
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Expected a canonical SHA-256')
    return dict(analysis_id=analysis_id, source_trace_sha256=source_sha,
                display_trace_sha256=display_sha,
                packet_namespace=('native_trace_packet_zero_based' if source_sha == display_sha
                                  else 'converted_trace_packet_zero_based'),
                native_version=native_version or 'UNKNOWN', segment_index=None)


def family(binding, name, subscription, count, retained, first, last, cap, *,
           reduction='none', filter_effect='UNKNOWN', done=True, refs=()):
    if any(type(v) is not int or v < 0 for v in (count, retained, cap)):
        raise ValueError('Invalid event counts')
    if retained > count or retained > cap:
        raise ValueError('Retained detail exceeds count or cap')
    if count == 0:
        if first is not None or last is not None:
            raise ValueError('Empty scope cannot contain an index')
    elif type(first) is not int or type(last) is not int or first < 0 or last < first:
        raise ValueError('Invalid event range')
    truncated = count > cap
    # Summaries may deliberately omit repeated states or bounded DLLP samples.
    # Even when the counter spans the traversal, details are not full packets.
    if truncated:
        completeness = 'TRUNCATED'
    elif count == 0:
        completeness = 'NOT_OBSERVED_IN_SCOPE'
    elif retained == count and done:
        completeness = 'OBSERVATION_COMPLETE_IN_DECLARED_SCOPE'
    else:
        completeness = 'SUMMARY_ONLY'
    return dict(**binding, family=name, subscription=subscription, channel_mask='all',
                native_index_namespace='packet', first_index=first, last_index=last,
                callback_count=count, record_count=retained, row_limit=cap,
                reduction=reduction, truncated=truncated, script_status='SCRIPT_DONE' if done else 'INCOMPLETE',
                event_level_completeness=completeness, filter_status=filter_effect,
                full_trace_coverage='UNKNOWN', evidence_refs=list(refs))


def tlp_coverage(binding, count, refs):
    n = count['tlp_callback_count']
    return family(binding, 'TLP', '_PACKET / _PKT_TLP / _ANY_TYPE', n, n,
                  count['first_tlp_index'] if n else None,
                  count['last_tlp_index'] if n else None, 100000000, refs=refs)
