#!/usr/bin/env python3
"""Export packet ranges of one trace to text through COM (ITrace.ExportToText), sending no GUI input.

Used to see what the decoded Trace View text contains with and without a file-based decoder.
Fails closed if PETracer is already running, the trace or protected files change, or PETracer
does not exit. Ranges are inclusive packet numbers, e.g. 8656:8662.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a1_com_g1a_probe import identity, log, petracer_pids  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--trace', type=Path, required=True, help='Read-only working copy')
    ap.add_argument('--range', action='append', required=True, help='from:to packet numbers (inclusive)')
    ap.add_argument('--protect', type=Path, action='append', default=[])
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    if args.output_dir.exists():
        print(f'Refusing existing output directory: {args.output_dir}', file=sys.stderr)
        return 2
    if petracer_pids():
        print('PETracer is already running; a COM run needs a clean start', file=sys.stderr)
        return 2
    ranges = [tuple(int(x) for x in r.split(':')) for r in args.range]
    args.output_dir.mkdir(parents=True)
    watched = [args.trace, *args.protect]
    run = {'schema': 'pcie.com-export-text/v1', 'started_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'input_sent_to_gui': 'none', 'pre': [identity(p) for p in watched], 'exports': []}
    trace = None
    try:
        pythoncom.CoInitialize()
        analyzer = win32com.client.Dispatch('CATC.PETracer')
        t = time.monotonic()
        trace = analyzer.OpenFile(str(args.trace))
        run['open_seconds'] = round(time.monotonic() - t, 1)
        for lo, hi in ranges:
            out = args.output_dir / f'packets-{lo}-{hi}.txt'
            try:
                trace.ExportToText(str(out), lo, hi)
                run['exports'].append({'range': [lo, hi], 'file': out.name, 'ok': out.exists(), 'bytes': out.stat().st_size if out.exists() else 0})
            except pythoncom.com_error as exc:
                run['exports'].append({'range': [lo, hi], 'ok': False, 'error': repr(exc)})
            log(f'export {lo}:{hi} -> {run["exports"][-1]}')
    except pythoncom.com_error as exc:
        run['com_error'] = repr(exc)
        log(f'COM error: {exc!r}')
    finally:
        try:
            if trace is not None:
                trace.Close()
        except pythoncom.com_error as exc:
            run['close_error'] = repr(exc)
        trace = analyzer = None
        pythoncom.CoUninitialize()
        deadline = time.monotonic() + 120
        while petracer_pids() and time.monotonic() < deadline:
            time.sleep(1)
        run['process_exit_ok'] = not petracer_pids()
    run['post'] = [identity(p) for p in watched]
    run['identities_unchanged'] = run['pre'] == run['post']
    ok = run['process_exit_ok'] and run['identities_unchanged'] and 'com_error' not in run and all(e.get('ok') for e in run['exports'])
    run['status'] = 'COM_EXPORT_COMPLETE' if ok else 'COM_EXPORT_FAILED'
    (args.output_dir / 'com-export.json').write_text(json.dumps(run, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: run[k] for k in ('status', 'identities_unchanged', 'process_exit_ok', 'exports')}, ensure_ascii=False, indent=2))
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
