"""PCIE-03: one .pex -> readonly copy -> existing VSE/verifiers -> G9 report.

Background worker is supervised independently of native selection. No policy,
failure-time input, PASS baseline, or new ranking rules are used. Native format
updates are confined to a disposable copy, sealed before readonly acquisition.
"""
from __future__ import annotations

import argparse
import gc
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

import pcie_navigation_probe as probe
import native_navigation as nav
import pcie_resources
import pcie_detail_windows as details
import pcie_large_io as large

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/pcie"
PROBES = {"count": "g1a-tlp-count.pevs", "rows": "g1c-tlp-rows-all.pevs",
          "fields": "g2a-tlp-fields.pevs", "messages": "g3c0-msg-fields.pevs"}
STAGE_PROBES = {"phase": "vopt-phase-scan.pevs", "transactions": "vopt-transactions.pevs"}
DENSE_PROBES = {"rows": "g1c-tlp-rows-batched.pevs", "fields": "g2a-tlp-fields-batched.pevs",
                "messages": "g3c0-msg-fields-batched.pevs"}


def selected_probes(request):
    if request.get('diagnostic_exports','full') not in ('full','on_demand'):raise ValueError('Unknown diagnostic export mode')
    if type(request.get('detail_windows',False)) is not bool:
        raise ValueError('detail_windows must be boolean')
    profile = request.get('extraction_profile', 'tlp-v1')
    if profile not in ('tlp-v1', 'stage-v1'):
        raise ValueError('Unknown PCIe extraction profile')
    if request.get('detail_windows') and profile!='stage-v1':raise ValueError('Detail windows require stage-v1')
    return dict(PROBES, **(STAGE_PROBES if profile == 'stage-v1' else {}))


def verified_step(function, args):
    with redirect_stdout(io.StringIO()) as output:
        code = function([str(arg) for arg in args])
    if code != 0:
        raise ValueError("extraction verifier rejected the data: " + function.__module__)
    return output.getvalue()


def finish_extraction(output, trace_info, diagnostic_exports='full'):
    """Use independent existing verifiers, not a new permissive import parser."""
    import verify_g1a_log as count
    import verify_g1b_rows as rows
    import verify_g2a_fields as fields
    import verify_g3c0_messages as messages
    import run_pcie_triage as triage
    logs = {name: output / (name + ".txt") for name in PROBES}
    summary = count.check_log(logs["count"].read_text(encoding="utf-8"))
    if summary['tlp_callback_count']>large.DEFAULTS['max_tlp_rows']:
        import pcie_dense_analysis
        return pcie_dense_analysis.finish(output,trace_info,summary['tlp_callback_count'],diagnostic_exports=diagnostic_exports)
    large.validate_bundle(output)
    large.check_rows(summary["tlp_callback_count"])
    if summary["tlp_callback_count"] == 0:
        result = {"status": "NO_TLP_OBSERVED", "findings_total": 0, "locators": [],
                  "coverage": "Successful count-only TLP subscription returned zero; other PCIe traffic is outside this analysis.",
                  "product_verdict": "NOT_EVALUATED", "ordering": "not_applicable"}
        probe.write(output / "analysis.json", result)
        return result
    verified_step(rows.main, [logs["rows"], "--g1a-log", logs["count"], "--output-dir", output / "verified-rows"])
    verified_step(fields.main, [logs["fields"], "--g1a-log", logs["count"], "--g1-rows", output / "verified-rows/rows.json",
                                "--output-dir", output / "verified-fields"])
    verified_step(messages.main, [logs["messages"], "--g1a-log", logs["count"], "--g2a-fields", output / "verified-fields/fields.json",
                                  "--output-dir", output / "verified-messages"])
    manifest = {"schema_version": "pcie.triage-input/v1", "trace":
                {"file_name": "display-working.pex", "sha256": trace_info["display_trace"]["sha256"],
                 "tlp_count": summary["tlp_callback_count"]}}
    original_sha = trace_info["source_trace"]["sha256"]
    if original_sha.lower() != manifest["trace"]["sha256"].lower():
        manifest["trace"]["provenance"] = {"original_sha256": original_sha,
            "conversion": trace_info.get("conversion_description", "Caller supplied a separate display trace; importer did not perform conversion."),
            "analysis_target": "display-working.pex", "packet_index_note": triage.g7_render_markdown.PACKET_INDEX_NOTE}
    for name in ("fields", "messages"):
        path = output / ("verified-" + name) / (name + ".json")
        manifest[name] = {"path": str(path), "sha256": nav.digest(path), "verifier_summary": str(path.parent / "summary.json")}
    probe.write(output / "triage-input.json", manifest)
    run = triage.run(output / "triage-input.json", output / "report")
    findings = json.loads((output / "report/findings.json").read_text(encoding="utf-8"))
    field_rows = json.loads((output / "verified-fields/fields.json").read_text(encoding="utf-8"))
    by_index = {row["packet_index"]: row for row in field_rows}
    locators = []
    for finding in findings["findings"]:
        index = finding["where_to_look"]["primary_go_to_packet"]
        row = by_index[index]
        locators.append({"finding_id": finding["finding_id"], "source_trace_sha256": original_sha,
            "display_trace_sha256": manifest["trace"]["sha256"],
            "packet_namespace": "converted_trace_packet_zero_based" if original_sha.lower() != manifest["trace"]["sha256"].lower()
                                else "native_trace_packet_zero_based",
            "display_level": 0, "packet_index": index, "timestamp": None,
            "time_display": row["time_display"], "time_precision": "vendor_display_text_only",
            "channel": row["channel"], "direction": row["channel"] if row["channel"] in ("Upstream", "Downstream") else "UNKNOWN"})
    result = {"status": "ANALYSIS_COMPLETE", "findings_total": run["findings_total"], "locators": locators,
              "ordering": findings["ordering"], "coverage": "Existing TLP association/message analysis only; no full PCIe compliance verdict.",
              "product_verdict": "NOT_EVALUATED", "native_navigation": "MANUAL_CTRL_G",
              "working_copy": str(output / "display-working.pex")}
    probe.write(output / "analysis.json", result)
    return result


class Cancelled(Exception):
    pass


def error_details(exc, stage):
    return dict(stage=stage, error=str(exc), hresult=getattr(exc, 'hresult', None),
                excepinfo=getattr(exc, 'excepinfo', None))


def fresh_copy(source, destination):
    # Never overwrite an existing path, symlink or original supplied by a caller.
    large.copy_new(source, destination)


def open_working_trace(analyzer, request, output, receipt, save):
    work = output / 'display-working.pex'
    receipt['stage'] = 'open_working_copy'; save()
    try:
        receipt.setdefault('native_open_attempts', []).append(dict(method='OpenFile',path=str(work)))
        save()
        return pcie_resources.timed(receipt,'initial_open',analyzer.OpenFile,str(work))
    except Exception as exc:
        receipt['initial_open_error'] = error_details(exc, 'open_working_copy')
        save()
    if (output / 'cancel.json').exists():
        raise Cancelled('Cancelled before working-copy conversion')
    receipt['stage'] = 'convert_working_copy'
    conversion = receipt['conversion'] = dict(status='preparing', method='OpenFile2', backup_option=False)
    save()
    try:
        open2 = getattr(analyzer, 'OpenFile2')
    except Exception as exc:
        conversion.update(status='unavailable', **error_details(exc, 'convert_working_copy')); save()
        raise RuntimeError('PETracer OpenFile2 is unavailable; native open failed') from None
    if nav.identity(work) != receipt['working_before'] or nav.verify_files(request) != receipt['before']:
        raise ValueError('Input changed before conversion')
    staged = output / 'conversion-working.pex'
    fresh_copy(work, staged)
    conversion['input'] = nav.identity(staged)
    if conversion['input']['sha256'] != request['display_trace']['sha256'].lower():
        raise ValueError('Conversion input hash mismatch')
    converting = None
    try:
        conversion['status'] = 'running'; save()
        # Vendor API updates THIS disposable file only. Original is never sent
        # to either native OpenFile method. No GUI setting or dialog automation.
        receipt.setdefault('native_open_attempts', []).append(dict(method='OpenFile2',path=str(staged)))
        save()
        converting = pcie_resources.timed(receipt,'conversion_open',open2,str(staged),False)
        conversion['open_succeeded'] = True
    except Exception as exc:
        conversion.update(status='failed', **error_details(exc, 'convert_working_copy'))
        raise
    finally:
        if converting is not None:
            conversion['close'] = nav.invoke(converting, 'Close')
        converting = None
        staged.chmod(0o444)
        conversion['output'] = nav.identity(staged); save()
    if not conversion.get('close', {}).get('ok'):
        conversion['status'] = 'close_failed'; save()
        raise RuntimeError('Native conversion trace close could not be confirmed')
    if (output / 'cancel.json').exists():
        raise Cancelled('Cancelled after working-copy conversion')
    if nav.verify_files(request) != receipt['before']:
        raise ValueError('Input changed during conversion')
    # Replace only the byte-verified copy we created in this fresh job folder.
    if nav.identity(work) != receipt['working_before']:
        raise ValueError('Working copy changed before conversion was sealed')
    work.chmod(0o666)
    try:
        shutil.copyfile(staged, work)
    finally:
        work.chmod(0o444)
    sealed = nav.identity(work)
    if sealed['sha256'] != conversion['output']['sha256']:
        raise ValueError('Converted display copy hash mismatch')
    receipt['working_before'] = sealed
    conversion['status'] = 'converted' if sealed['sha256'] != conversion['input']['sha256'] else 'unchanged'
    receipt['stage'] = 'reopen_converted_copy'; save()
    receipt.setdefault('native_open_attempts', []).append(dict(method='OpenFile',path=str(work)))
    save()
    return pcie_resources.timed(receipt,'converted_reopen',analyzer.OpenFile,str(work))


def extraction_input(request, receipt, output):
    """Bind analysis to the sealed display bytes; never reuse original indices."""
    working = nav.identity(output / 'display-working.pex')
    if working != receipt['working_before'] or not working['readonly']:
        raise ValueError('Analysis copy is not sealed')
    conversion = receipt.get('conversion')
    if conversion:
        staged = output / 'conversion-working.pex'
        if (conversion.get('status') not in ('converted', 'unchanged')
                or conversion.get('method') != 'OpenFile2'
                or conversion.get('open_succeeded') is not True
                or conversion.get('close', {}).get('ok') is not True
                or conversion.get('input', {}).get('sha256') != request['display_trace']['sha256'].lower()
                or conversion.get('output') != nav.identity(staged)
                or conversion['output']['sha256'] != working['sha256']
                or not conversion['output']['readonly']):
            raise ValueError('Converted copy provenance not established')
    elif working['sha256'] != request['display_trace']['sha256'].lower():
        raise ValueError('Display copy differs from imported trace')
    return dict(source_trace=request['source_trace'], display_trace=working,
                conversion_description='PETracer OpenFile2 updated a disposable working copy; source untouched. Packet numbering belongs to the converted display copy.'
                if conversion else 'Caller supplied a separate display trace; importer did not perform conversion.')


def classify_cleanup(receipt):
    # An OpenFile failure creates no trace to Close. Absence of that receipt
    # cannot turn a clean process exit into a cleanup failure.
    conversion = receipt.get('conversion', {})
    close_failed = (any(x.get('ok') is False for x in
                       [receipt.get('close', {}), conversion.get('close', {})])
                    or (receipt.get('open_file_count', 0) > 0 and not receipt.get('close', {}).get('ok'))
                    or (conversion.get('open_succeeded') and not conversion.get('close', {}).get('ok')))
    unknown = bool(receipt.get('created_pids') and (receipt.get('remaining_pids') or close_failed
                   or any(not d['ok'] for d in receipt.get('event_disconnects', []))))
    receipt['cleanup_status'] = 'unconfirmed' if unknown else 'confirmed'
    if unknown:
        receipt['operation_status'] = receipt['status']
        if receipt['status'] != 'INTEGRITY_FAILED':
            receipt['status'] = 'NATIVE_CLEANUP_UNCONFIRMED'


def worker(request_path, output):
    from pcie_navigation_service import exclusive
    try:
        with exclusive():
            return _worker(request_path, output)
    except Exception as exc:
        probe.write(output / 'worker.json', dict(status='FAILED', error=str(exc), stage='preflight'))
        return 2


def _worker(request_path, output):
    worker_started=time.monotonic()
    import pythoncom
    import win32com.client
    from a1_com_g1a_probe import EVENTS, VseEvents
    request = json.loads(request_path.read_text(encoding="utf-8"))
    limits = large.policy(request.get('resource_policy'))
    probes = selected_probes(request)
    before = nav.verify_files(request)
    receipt = {"status": "RUNNING", "stage": "preflight", "before": before, "probes": [],
               "open_file_count": 0, "coexistence": "RESTRICTED_NO_EXISTING_SESSION",
               "extraction_profile": request.get('extraction_profile', 'tlp-v1'),
               "resource_policy":limits}
    def save(): probe.write(output / "worker.json", receipt)
    save()
    trace = analyzer = engine = engine_disp = None
    initialized = False
    active = False
    preliminary = None
    spool = None
    try:
        if (output / 'cancel.json').exists(): raise Cancelled('Cancelled before native acquisition')
        receipt["existing_pids"] = probe.processes()
        if receipt["existing_pids"]:
            receipt["status"] = "EXISTING_SESSION_BLOCKED"
            return 2
        receipt["capabilities"] = probe.capabilities()
        work = output / "display-working.pex"
        receipt['stage']='copy_working_trace';save()
        pcie_resources.timed(receipt,'working_copy',large.copy_new,
            request["display_trace"]["path"],work,limits=limits,
            cancelled=lambda:(output/'cancel.json').exists())
        work.chmod(0o444)
        receipt["working_before"] = nav.identity(work)
        if receipt["working_before"]["sha256"] != before["display_trace"]["sha256"]:
            raise ValueError("working copy hash mismatch")
        script_files=dict(probes,**{'dense_'+key:name for key,name in DENSE_PROBES.items()})
        receipt["scripts_before"] = {key: nav.identity(SCRIPTS / filename) for key, filename in script_files.items()}
        if probe.processes():
            receipt["status"] = "EXISTING_SESSION_BLOCKED"
            return 2
        pythoncom.CoInitialize(); initialized = True
        receipt["stage"] = "create_com"; save()
        analyzer = pcie_resources.timed(receipt,'com_dispatch',win32com.client.Dispatch,"CATC.PETracer")
        receipt["created_pids"] = probe.processes()
        if len(receipt["created_pids"]) != 1:
            raise ValueError("ambiguous native ownership; no file opened")
        opening=time.monotonic()
        trace = open_working_trace(analyzer, request, output, receipt, save)
        receipt['open_elapsed_seconds']=time.monotonic()-opening
        receipt["open_file_count"] = 1
        receipt['analysis_input'] = extraction_input(request, receipt, output)
        receipt["native_packet_count"] = int(trace.GetPacketsCountEx())
        receipt["subscription"] = {
            "event": "_PKT_TLP", "tlp_type": "_ANY_TYPE", "channels": "all",
            "range": "natural trace traversal", "rows_cap": 100000000,
            "sampling": False, "display_filter_effect": "UNKNOWN",
            "excluded": ["DLLP", "ordered sets", "Link conditions", "electrical idle"],
            "done_means": "VSE execution completed; not whole-protocol coverage"}
        no_tlp = False
        for name, filename in probes.items():
            if receipt.get('storage_mode')=='pcie.disk-index/v1':
                filename=DENSE_PROBES.get(name,filename)
            if no_tlp and name in ('rows','fields','messages'): continue
            if (output / 'cancel.json').exists(): raise Cancelled('Cancelled between native probes')
            receipt["stage"] = "extract_" + name; save()
            spool=large.ReportSpool(output/(name+".txt"),limits)
            EVENTS["lines"] = spool; EVENTS["finished"] = None
            engine_disp = trace.GetVScriptEngine(str(SCRIPTS / filename))
            engine = win32com.client.WithEvents(engine_disp, VseEvents)
            engine_disp.Tag = len(receipt["probes"]) + 1
            started = last_saved = time.monotonic()
            active = True
            engine_disp.LaunchVScript()
            while EVENTS["finished"] is None:
                pythoncom.PumpWaitingMessages()
                spool.check()
                if time.monotonic() - last_saved >= 2:
                    spool.flush()
                    receipt['output_progress']=dict(probe=name,lines=spool.lines,records=spool.records,bytes=spool.bytes)
                    save()
                    last_saved = time.monotonic()
                # ReportText callbacks are synchronous COM calls. A 50 ms
                # polling delay can add that delay to every emitted row.
                # Keep a bounded idle yield without throttling evidence rows.
                time.sleep(0 if receipt.get('storage_mode')=='pcie.disk-index/v1' else 0.005)
            active = False
            # Drain queued final report callbacks as in the qualified COM runner.
            for _ in range(20): pythoncom.PumpWaitingMessages(); time.sleep(0.05)
            log = output / (name + ".txt")
            spool.finish(EVENTS["finished"]["result"])
            receipt["probes"].append({"name": name, "finished": EVENTS["finished"],
                                      "script":filename,
                                      "elapsed_seconds": time.monotonic() - started, "log_sha256": nav.digest(log),
                                      "output_bytes":spool.bytes,"callback_count":spool.lines})
            spool=None
            # WithEvents retains a COM connection-point reference cycle. Dropping
            # Python variables alone may keep PETracer alive until worker exit.
            # Explicitly unadvise before releasing each completed engine.
            disconnected = nav.invoke(engine, "close")
            receipt.setdefault("event_disconnects", []).append(disconnected)
            engine = engine_disp = None; save()
            if not disconnected["ok"]:
                raise ValueError("VSE event connection could not be released")
            if EVENTS["finished"]["result"] != 2:
                raise ValueError("VSE did not finish DONE: " + name)
            if name == "count":
                from verify_g1a_log import check_log
                tlp_count=check_log(log.read_text(encoding="utf-8"))["tlp_callback_count"]
                receipt['tlp_count']=tlp_count
                if tlp_count>limits['max_tlp_rows']:
                    # Large raw outputs are allowed only with the disk-backed verifier path.
                    receipt['storage_mode']='pcie.disk-index/v1'
                    limits=dict(limits,max_probe_bytes=limits['dense_probe_bytes'])
                    receipt['effective_probe_disk_budget']=limits['max_probe_bytes'];save()
                no_tlp = tlp_count == 0
        if request.get('detail_windows') and request.get('extraction_profile')=='stage-v1':
            import pcie_phase_evidence as phase_data
            import pcie_event_coverage as scope
            import pcie_stage_summary as stages
            receipt['stage']='prepare_detail_windows';save()
            preliminary=pcie_resources.timed(receipt,'initial_verify_and_analyze',finish_extraction,output,receipt['analysis_input'],diagnostic_exports=request.get('diagnostic_exports','full'))
            binding=scope.identity(uuid.uuid4().hex,receipt['analysis_input']['source_trace']['sha256'],
                receipt['analysis_input']['display_trace']['sha256'],receipt['capabilities']['file_version'])
            phase=phase_data.load(output,next(p for p in receipt['probes'] if p['name']=='phase'),binding,receipt['native_packet_count'])
            fields_path=output/'verified-fields/fields.json'
            if (output/'disk-index.json').exists():
                import pcie_disk_index
                fields=pcie_disk_index.Fields(output/'transactions.sqlite')
            else:fields=json.loads(fields_path.read_text(encoding='utf-8')) if fields_path.exists() else []
            try:summary=stages.summarize(phase,fields,binding)
            finally:
                if hasattr(fields,'close'):fields.close()
            windows=details.propose(preliminary['locators'],summary,receipt['native_packet_count'])
            receipt['stage']='extract_detail_windows';save()
            detail_binding={k:binding[k] for k in ('source_trace_sha256','display_trace_sha256','packet_namespace')}
            detail_result=details.acquire(trace,output,work,detail_binding,windows,lambda:(output/'cancel.json').exists())
            probe.write(output/'detail-windows.json',detail_result)
            receipt['native_details']=dict(sha256=nav.digest(output/'detail-windows.json'),status=detail_result['status'],
                windows=len(windows),packet_count=detail_result['packet_count'])
        receipt["status"] = "EXTRACTION_COMPLETE"
        if (output / 'cancel.json').exists(): raise Cancelled('Cancelled after acquisition')
    except Cancelled as exc:
        receipt.update(status='CANCELLED', error=str(exc), native_cancelled=False)
    except InterruptedError as exc:
        receipt.update(status='CANCELLED', error=str(exc), native_cancelled=False)
    except Exception as exc:
        receipt.update(status="FAILED", error=str(exc), hresult=getattr(exc, "hresult", None),
                       excepinfo=getattr(exc, "excepinfo", None))
        receipt['primary_error'] = error_details(exc, receipt['stage'])
    finally:
        if spool is not None:
            try:spool.close()
            except OSError as exc:receipt.setdefault('spool_close_error',str(exc))
        receipt['native_peak_working_set_bytes']={str(pid):pcie_resources.peak_bytes(pid) for pid in receipt.get('created_pids',[])}
        if engine is not None:
            receipt.setdefault("event_disconnects", []).append(nav.invoke(engine, "close"))
        engine = engine_disp = None
        if trace is not None and not active:
            receipt["stage"] = "close_owned_trace"
            try:
                save()
            except OSError as exc:
                # A progress-file failure must not skip owned trace cleanup.
                # The final receipt still has to persist before any success.
                receipt.setdefault('receipt_write_errors', []).append(str(exc))
            receipt["close"] = pcie_resources.timed(receipt,'native_close',nav.invoke,trace,"Close")
        trace = analyzer = None
        if initialized:
            # Dispatch/event wrappers can retain reference cycles even after
            # unadvise. Release those proxies while this STA is initialized;
            # waiting for process exit otherwise produces a false cleanup stop.
            receipt['released_proxy_cycles']=gc.collect()
            pythoncom.CoUninitialize()
        if receipt.get("created_pids"):
            cleanup_started=time.monotonic()
            # Local 13.26 can take about 15.5 s to exit after successful Close.
            # Keep the same fail-closed predicate, allowing a bounded grace
            # period rather than treating Close's return as process cleanup.
            deadline = cleanup_started + 30
            while probe.processes() and time.monotonic() < deadline: time.sleep(0.2)
            receipt['cleanup_wait_seconds']=time.monotonic()-cleanup_started
        receipt["remaining_pids"] = probe.processes()
        try:
            receipt["after"] = nav.verify_files(request)
            receipt["inputs_unchanged"] = before == receipt["after"]
            if "working_before" in receipt:
                receipt["working_after"] = nav.identity(work)
                receipt["working_unchanged"] = receipt["working_before"] == receipt["working_after"]
            if "scripts_before" in receipt:
                receipt["scripts_after"] = {key: nav.identity(SCRIPTS / filename) for key, filename in script_files.items()}
                receipt["scripts_unchanged"] = receipt["scripts_before"] == receipt["scripts_after"]
        except Exception as exc:
            receipt.update(inputs_unchanged=False, integrity_error=str(exc))
        if any(receipt.get(k) is False for k in ("inputs_unchanged", "working_unchanged", "scripts_unchanged")):
            receipt["status"] = "INTEGRITY_FAILED"
        classify_cleanup(receipt)
        receipt['worker_peak_working_set_bytes']=pcie_resources.peak_bytes(os.getpid())
        receipt['elapsed_seconds']=time.monotonic()-worker_started
        save()
    if receipt["status"] != "EXTRACTION_COMPLETE": return 2
    receipt["stage"] = "verify_and_analyze"; save()
    verifying=time.monotonic()
    try:
        result = preliminary if preliminary is not None else finish_extraction(output, receipt['analysis_input'],request.get('diagnostic_exports','full'))
        receipt.update(stage="finished", status=result["status"], findings_total=result["findings_total"])
    except Exception as exc:
        receipt.update(status="ANALYSIS_FAILED", error=str(exc))
    receipt['verify_analyze_elapsed_seconds']=time.monotonic()-verifying
    receipt['elapsed_seconds']=time.monotonic()-worker_started
    receipt['worker_peak_working_set_bytes']=pcie_resources.peak_bytes(os.getpid())
    receipt['export_bytes']=sum((output/(p['name']+'.txt')).stat().st_size for p in receipt['probes'])
    save()
    return 0 if receipt["status"] in ("ANALYSIS_COMPLETE", "NO_TLP_OBSERVED") else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--original", type=Path, help="Optional pre-conversion source; hashed only")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--profile", choices=('tlp-v1','stage-v1'), default='stage-v1')
    parser.add_argument("--detail-windows", action='store_true', help='Bounded native evidence around current candidates and last observed stage')
    parser.add_argument("--worker-request", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if args.worker_request: return worker(args.worker_request, output)
    if not args.trace or args.trace.suffix.lower() != ".pex": parser.error("a .pex trace is required")
    if args.detail_windows and args.profile!='stage-v1':parser.error('detail windows require stage-v1')
    if output.exists(): parser.error("fresh output directory required")
    if not probe.math_is_positive(args.timeout): parser.error("positive finite timeout required")
    source = (args.original or args.trace).resolve(); display = args.trace.resolve()
    request = {"source_trace": nav.identity(source), "display_trace": nav.identity(display),
               "extraction_profile": args.profile, "detail_windows":args.detail_windows}
    output.mkdir(parents=True); probe.write(output / "request.json", request)
    result = probe.supervise([sys.executable, str(Path(__file__).resolve()), "--worker-request", str(output / "request.json"),
                             "--output", str(output)], output, args.timeout)
    try:
        result["inputs_unchanged"] = nav.verify_files(request) == {k:request[k] for k in ('source_trace','display_trace')}
    except Exception as exc:
        result.update(inputs_unchanged=False, integrity_error=str(exc))
    result["remaining_native_pids"] = probe.processes()
    probe.write(output / "supervisor.json", result)
    print(json.dumps(result))
    if not result["inputs_unchanged"]: return 3
    return result["worker_exit_code"] if result["status"] == "WORKER_EXITED" else 4


if __name__ == "__main__": raise SystemExit(main())
