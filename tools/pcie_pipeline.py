"""Background PCIe job adapter for the existing desktop controller."""
from __future__ import annotations
import json
from pathlib import Path
from contextlib import contextmanager
import subprocess
import sys
import time

import pcie_navigation_probe as probe
import native_navigation as nav
import pcie_workspace as view

STAGES={'preflight':'檢查 PCIe 執行環境', 'create_com':'啟動專用 PETracer 工作',
        'copy_working_trace':'建立工作副本；分塊讀取，不修改原檔',
        'open_working_copy':'開啟唯讀工作副本',
        'convert_working_copy':'嘗試在工作副本轉換舊格式；原始檔不變',
        'reopen_converted_copy':'核對轉換後副本並以唯讀方式重新開啟', 'extract_count':'擷取 TLP 計數',
        'extract_rows':'擷取 TLP 列', 'extract_fields':'擷取交易欄位',
        'extract_messages':'擷取 Message 欄位', 'close_owned_trace':'核對原生工作清理',
        'extract_phase':'擷取 Link／LTSSM 階段與有上限的 DLLP 摘要',
        'extract_transactions':'核對原生 Config／Completion 交易層',
        'prepare_detail_windows':'核對全量交易、建立磁碟索引與候選',
        'extract_detail_windows':'擷取候選與階段附近的原生 Packet 明細',
        'verify_and_analyze':'驗證來源與關聯分析', 'finished':'準備候選與證據'}


class Cancelled(Exception):pass
class Partial(RuntimeError):pass
class CleanupUnknown(RuntimeError):pass


def progress_text(receipt, stage, seconds, warning_seconds):
    message=STAGES.get(stage,stage or '準備中')+f'；本階段已等待 {int(seconds)} 秒'
    output=receipt.get('output_progress')
    if output and stage=='extract_'+output.get('probe',''):
        if 'records' in output:
            message+=f"；已輸出 {output['records']:,} 文字列、{output['bytes']/1048576:.1f} MiB"
        else:message+=f"；已輸出 {output['lines']:,} 次回報、{output['bytes']/1048576:.1f} MiB"
        if receipt.get('tlp_count') and stage in ('extract_rows','extract_fields'):
            message+=f"；獨立 TLP 計數 {receipt['tlp_count']:,}（尾端待驗證）"
    elif seconds>warning_seconds:
        message+=('；正在處理完整交易與證據，尚未完成分析。' if stage in ('prepare_detail_windows','verify_and_analyze') else '；原生呼叫未回報新的階段完成，仍在監測。')
    return message


@contextmanager
def supervised_worker(process, output):
    """An observer/UI I/O failure must not orphan a still-running tool worker."""
    try:
        yield
    except Exception as exc:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
            try:
                probe.write(output/'supervisor.json',dict(status='OBSERVER_FAILED',error=str(exc),
                    worker_pid=process.pid,native_cleanup='UNKNOWN',native_cancelled='UNKNOWN',
                    candidates_published=False))
            except OSError:
                pass  # A full/failed volume cannot be repaired by another write.
            raise CleanupUnknown('狀態或監測更新失敗；僅停止工具 worker，PETracer 清理未知。請保留日誌並核對原生工作：'+str(exc)) from exc
        raise


def failure_message(receipt):
    if receipt.get('status')=='WORKER_ABORTED':
        return '背景分析程序已提早結束；最後狀態紀錄尚未完成，不代表仍在分析。請查看 analysis.log 與 supervisor.json；原生清理狀態需另外核對。'
    if receipt.get('status')=='INTEGRITY_FAILED':
        return '來源、工作副本或擷取腳本的完整性檢查未通過；停止產生候選，請查看 worker.json。'
    primary=receipt.get('primary_error',{})
    stage=primary.get('stage',receipt.get('stage'))
    error=primary.get('error',receipt.get('error','請查看 analysis.log 與 worker.json'))
    if stage in ('open_working_copy','convert_working_copy','reopen_converted_copy'):
        conversion=receipt.get('conversion',{})
        if conversion.get('status')=='unavailable':
            summary='PETracer 無法開啟此檔案；目前版本未提供可用的自動格式轉換介面。'
        elif stage=='convert_working_copy':
            summary='PETracer 開檔失敗，工作副本的自動格式轉換也未完成。'
        elif stage=='reopen_converted_copy':
            summary='工作副本格式處理後，PETracer 仍無法重新開啟。'
        else:summary='PETracer 無法開啟工作副本，尚未開始分析。'
        original=receipt.get('initial_open_error',{}).get('error')
        detail=(' 最初開檔錯誤：'+original) if original and original!=error else ''
        return summary+' 原始檔未交給 PETracer 修改。請用 PETracer 開啟另一份副本，完成格式更新後再匯入。原生錯誤：'+str(error)+detail
    return 'PCIe 分析未完成：'+str(receipt.get('status','FAILED'))+'；'+str(error)


def run(source, output, analysis_id, progress=lambda text:None, timeout=None, cancel=None, cache_root=None):
    import pcie_large_io as large
    import pcie_resources as resources
    import os
    import tempfile
    overall_started=time.monotonic()
    limits=large.policy()
    if timeout is not None:
        if not probe.math_is_positive(timeout):raise ValueError('positive timeout required')
        import math
        limits['total_seconds']=max(1,math.ceil(timeout))
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if source.suffix.lower()!='.pex' or not source.is_file():raise ValueError('請匯入單一 .pex 檔案')
    if probe.processes():raise RuntimeError('EXISTING_SESSION_BLOCKED：PETracer 已有工作階段，工具未接管。請保留原工作並稍後重試。')
    progress('驗證來源身分；分塊讀取原檔，不修改原檔。')
    try:before=large.identity(source,cancelled=lambda:cancel is not None and cancel.is_set())
    except InterruptedError as exc:raise Cancelled(str(exc)) from exc
    output.mkdir(parents=True,exist_ok=False)
    large.check_disk(output,2*before['bytes'],limits['disk_reserve_bytes'])
    large.check_disk(tempfile.gettempdir(),0,limits['disk_reserve_bytes'])
    request=dict(source_trace=before,display_trace=before,extraction_profile='stage-v1',detail_windows=True,diagnostic_exports='on_demand',
                 resource_policy=limits)
    cache_key=cache_binding=None
    cache_receipt=dict(reuse='NONE',analysis_cache='DISABLED_UNKNOWN_FILTERS')
    if cache_root is not None:
        import pcie_conversion_cache as cache
        try:
            cache_key,cache_binding=cache.key_for(before,probe.capabilities())
            cached,reason=cache.lookup(cache_root,cache_key,cache_binding)
            cache_receipt.update(lookup=reason,key=cache_key)
            if cached:
                request['display_trace']=cached
                cache_receipt['reuse']='VERIFIED_FORMAT_CONVERSION_ONLY'
                request['conversion_cache']=dict(key=cache_key,binding=cache_binding,display=cached)
                progress('已核對格式轉換副本；重新建立工作副本並重新擷取，不重用先前情境或分析。')
        except (OSError,ValueError,KeyError) as exc:
            cache_receipt['lookup_error']=str(exc)
    probe.write(output/'cache.json',cache_receipt)
    probe.write(output/'request.json',request)
    started=time.monotonic();stage=None;stage_started=started;last_sample=0;last_progress=0
    receipt={}
    with (output/'analysis.log').open('wb') as log, (output/'resources.jsonl').open('x',encoding='utf-8') as samples:
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('pcie_trace_import.py')),
                '--worker-request',str(output/'request.json'),'--output',str(output)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        probe.write(output/'active-worker.json',dict(pid=process.pid,analysis_id=analysis_id))
        with supervised_worker(process, output):
            while process.poll() is None:
                if cancel is not None and cancel.is_set() and not (output/'cancel.json').exists():
                    probe.write(output/'cancel.json',dict(requested=True,mode='between_native_calls'))
                    progress('已要求取消，等待目前原生呼叫安全結束；尚未宣告取消完成。')
                path=output/'worker.json'
                if path.exists():
                    receipt=probe.read_json(path)
                    current=receipt.get('stage')
                    if current!=stage:
                        stage=current;stage_started=time.monotonic();progress(STAGES.get(stage,stage or '準備中'))
                now=time.monotonic()
                resource_error=None
                if now-last_sample>=1:
                    observed=[resources.sample(pid) for pid in [os.getpid(),process.pid,*receipt.get('created_pids',[])]]
                    samples.write(json.dumps(dict(seconds=now-started,stage=stage,
                        processes=observed,output_progress=receipt.get('output_progress')),ensure_ascii=False)+'\n')
                    samples.flush();last_sample=now
                    for item in observed:
                        if not item:continue
                        key=('controller_private_bytes' if item['pid']==os.getpid() else
                             'worker_private_bytes' if item['pid']==process.pid else 'native_private_bytes')
                        if item['private_commit_bytes']>limits[key]:
                            resource_error=f"程序 {item['pid']} 記憶體超過本機安全設定 {key}={limits[key]} bytes"
                    try:
                        large.check_disk(output,0,limits['disk_reserve_bytes'])
                        large.check_disk(tempfile.gettempdir(),0,limits['disk_reserve_bytes'])
                    except large.ResourceLimit as exc:resource_error=str(exc)
                if now-last_progress>=5:
                    progress(progress_text(receipt,stage,now-stage_started,limits['no_progress_warning_seconds']))
                    last_progress=now
                if (now-started>limits['total_seconds'] or now-stage_started>large.stage_deadline(stage,limits)
                        or resource_error):
                    process.kill();process.wait(timeout=5)
                    probe.write(output/'supervisor.json',dict(status='RESOURCE_LIMIT' if resource_error else 'TIMEOUT',
                        worker_pid=process.pid,stage=stage,error=resource_error,native_cancelled='UNKNOWN',
                        native_cleanup='UNKNOWN',candidates_published=False,inputs_unchanged=nav.identity(source)==before))
                    raise CleanupUnknown((resource_error or 'PCIe 原生呼叫逾時')+'；僅停止工具 worker。PETracer 取消／清理未知，保留副本與日誌，請先核對原生狀態。')
                time.sleep(.2)
    receipt=probe.read_json(output/'worker.json') if (output/'worker.json').exists() else {}
    if nav.identity(source)!=before:raise ValueError('來源在分析過程發生變更，停止產生候選')
    if receipt.get('status') in ('RUNNING','EXTRACTION_COMPLETE'):
        probe.write(output/'supervisor.json',dict(status='WORKER_ABORTED',worker_pid=process.pid,
            returncode=process.returncode,last_recorded_status=receipt['status'],
            last_recorded_stage=receipt.get('stage'),native_cleanup='UNKNOWN',candidates_published=False))
        # Preserve the original worker receipt as evidence, even if it is stale.
        receipt=dict(receipt,status='WORKER_ABORTED')
    if receipt.get('status')=='CANCELLED':raise Cancelled('已在原生呼叫之間安全停止；副本與日誌已保留。')
    if receipt.get('status')=='NATIVE_CLEANUP_UNCONFIRMED':
        detail=(failure_message(receipt)+'\n') if receipt.get('primary_error') else ''
        raise CleanupUnknown(detail+('另有 ' if detail else '')+'PETracer 清理未確認；保留工作副本，請先確認原生程序狀態。')
    if process.returncode or receipt.get('status') not in ('ANALYSIS_COMPLETE','NO_TLP_OBSERVED'):
        failure=Partial if receipt.get('probes') else RuntimeError
        probe.write(output/'coverage.json',dict(status='partial' if receipt.get('probes') else 'failed',
            native_packet_count=receipt.get('native_packet_count'),completed_probes=[p['name'] for p in receipt.get('probes',[]) if p.get('finished',{}).get('result')==2],
            full_trace_coverage='UNKNOWN',candidates_published=False))
        raise failure(failure_message(receipt))
    if cancel is not None and cancel.is_set():raise Cancelled('分析結束後已取消呈現；未使用結果，副本與日誌已保留。')
    progress('驗證候選來源、擷取範圍與報告')
    large.validate_bundle(output)
    import pcie_model_worker
    try:model=pcie_model_worker.compose(output,analysis_id,cancel,progress)
    except InterruptedError as exc:raise Cancelled(str(exc)) from exc
    probe.write(output/'coverage.json',model['coverage'])
    probe.write(output/'stage-summary.json',model['stage_summary'])
    if model['transaction_crosscheck'] is not None:
        probe.write(output/'transaction-crosscheck.json',model['transaction_crosscheck'])
    if cache_root is not None and cache_key and not request.get('conversion_cache'):
        try:cache_receipt['store']=cache.store(cache_root,cache_key,cache_binding,output/'display-working.pex',receipt,
            cancelled=lambda:cancel is not None and cancel.is_set())
        except InterruptedError as exc:raise Cancelled(str(exc)) from exc
        except (OSError,ValueError) as exc:cache_receipt['store_error']=str(exc)
        probe.write(output/'cache.json',cache_receipt)
    if cancel is not None and cancel.is_set():raise Cancelled('已取消報告發布；本次結果未使用，原生清理已確認。')
    probe.write(output/'pipeline-timing.json',dict(source_preparation_seconds=started-overall_started,
        pipeline_seconds=time.monotonic()-started,through_model_seconds=time.monotonic()-overall_started,
        ui_interactive='NOT_MEASURED_HERE',resource_policy=limits))
    return dict(model=model,working=output/'display-working.pex',source_before=before,elapsed_seconds=time.monotonic()-started)
