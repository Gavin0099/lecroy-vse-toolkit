"""Local USB2 EP0 tool controller; discovery is imported unchanged.

The browser can select only an already-bound candidate. Native file paths enter
through CLI/native stdin IPC, never through HTTP. No network or shell dependency.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import usb_control_triage as engine
import usb_triage_model as presentation

HERE = Path(__file__).resolve().parent
POWERSHELL = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
NATIVE_MUTEX_NAME = r'Local\LeCroyTraceTriage.Native'


def powershell_environment():
    env = os.environ.copy()
    # A Python process can inherit PowerShell 7's module path. Windows PS 5.1
    # then picks incompatible Utility modules (e.g. Get-FileHash disappears).
    env['PSModulePath'] = str(Path(POWERSHELL).parent / 'Modules')
    env['PYTHONUTF8'] = '1'
    return env


@contextmanager
def native_exclusive():
    """Share the same per-Windows-session mutex as the COM STA worker."""
    if os.name != 'nt':
        yield
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.ReleaseMutex.argtypes = kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, NATIVE_MUTEX_NAME)
    if not handle:
        raise OSError('Cannot create native-session mutex')
    acquired = False
    try:
        acquired = kernel.WaitForSingleObject(handle, 0) in (0, 0x80)
        if not acquired:
            raise RuntimeError('另一個工具工作階段正在使用 LeCroy，請稍後重試。')
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def snapshot(path, cancel=None):
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            if cancel is not None and cancel.is_set():
                raise InterruptedError('已取消來源驗證；尚未啟動原生分析。')
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Trace changed while reading')
    return {'sha256': digest.hexdigest(), 'size': after.st_size,
            'mtime_ns': after.st_mtime_ns, 'mode': after.st_mode}


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    deadline=time.monotonic()+2
    while True:
        try:
            os.replace(temp,path)
            return
        except PermissionError as exc:
            if getattr(exc,'winerror',None) not in (5,32,33) or time.monotonic()>=deadline:
                raise
            time.sleep(.05)


def process_peak_bytes(pid):
    """Observed OS process-lifetime working-set peak; unavailable stays unknown."""
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in
            ('peak_ws','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return None
    try:
        counter = Counters();counter.cb = ctypes.sizeof(counter)
        return int(counter.peak_ws) if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counter), counter.cb) else None
    finally:
        kernel.CloseHandle(handle)


def sample_resources(output, wrapper_pid, result):
    for pid, role in [(os.getpid(), 'controller'), (wrapper_pid, 'acquisition_wrapper')] + [(p, 'observed_UsbSuite') for p in servers()]:
        peak = process_peak_bytes(pid)
        if peak is not None:
            result['process_peaks'][str(pid)] = {'role': role, 'observed_os_lifetime_peak_working_set_bytes': peak}
    size = sum(p.stat().st_size for p in Path(output).rglob('*') if p.is_file()) if Path(output).exists() else 0
    result['sampled_workdir_peak_bytes'] = max(size, result['sampled_workdir_peak_bytes'])


def servers():
    if os.name != 'nt':
        return []
    # tasklist is a fixed read-only process query, not a shell-built command.
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UsbSuite.exe', '/FO', 'CSV', '/NH'],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    import csv
    rows = csv.reader(result.stdout.decode('mbcs', errors='replace').splitlines())
    return sorted(int(row[1]) for row in rows if len(row) > 1 and row[0].lower() == 'usbsuite.exe')


def validate_model(model):
    if model.get('format') == 'pcie-triage-inspection/v1':
        import pcie_workspace
        return pcie_workspace.validate(model)
    if model.get('format') == presentation.FORMAT:
        return presentation.validate(model)
    if model.get('format') != 'usb-control-inspection/v1':
        raise ValueError('Unsupported inspection format')
    digest = model.get('trace_sha256', '')
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid trace identity')
    cards = model.get('candidates')
    if not isinstance(cards, list) or len(cards) > 3:
        raise ValueError('Invalid candidates')
    for rank, card in enumerate(cards, 1):
        ids = card.get('transfer_indices')
        if card.get('rank') != rank or not isinstance(ids, list) or not ids:
            raise ValueError('Invalid candidate identity')
        if any(type(i) is not int or not 0 <= i <= 2147483647 for i in ids):
            raise ValueError('Invalid native Transfer index')
    return model


class NativeWorker:
    def __init__(self, directory, binding):
        self.root = Path(directory)
        self.root.mkdir()
        atomic_json(self.root / 'binding.json', binding)
        self.log = (self.root / 'worker.log').open('wb')
        self.proc = subprocess.Popen([POWERSHELL, '-NoProfile', '-STA', '-File',
                                     str(HERE / 'usb-control-navigation.ps1'), '-SessionDirectory', str(self.root)],
                                    stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW, env=powershell_environment())

    def request(self, action, transfer=None, timeout=90):
        until = time.monotonic() + timeout
        while not (self.root / 'ready.json').exists():
            if self.proc.poll() is not None:
                raise RuntimeError('Navigation worker failed; see worker.log')
            if time.monotonic() > until:
                raise TimeoutError('Navigation worker did not start')
            time.sleep(.1)
        identity = uuid.uuid4().hex
        payload = {'target': transfer} if isinstance(transfer, dict) else {'transfer': transfer}
        atomic_json(self.root / 'request.json', {'id': identity, 'action': action, **payload})
        while time.monotonic() < until:
            response = self.root / 'response.json'
            if response.exists():
                try:
                    value = json.loads(response.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    time.sleep(.05)
                    continue
                if value.get('id') == identity:
                    return value
            if self.proc.poll() is not None:
                raise RuntimeError('Navigation worker exited unexpectedly')
            time.sleep(.1)
        raise TimeoutError('LeCroy 無回應；定位結果未知。停止重試，請先結束本次工作。')

    def close(self, timeout=15):
        if self.proc.poll() is None:
            response = self.request('close', timeout=timeout)
            if response.get('state') != 'closed':
                raise RuntimeError('Native cleanup not confirmed')
            self.proc.wait(timeout=timeout)
        self.log.close()


def config_ur_locators(result):
    """Only the selected case's verified events can become native commands."""
    count = result['native_packet_count']
    binding = {key:result[key] for key in ('source_trace_sha256','display_trace_sha256','packet_namespace')}
    locators = {}
    for row in result['rows']:
        readback = row['readback'] or {}
        events = dict(request=row['request'],completion=row['completion'],
                      read_request=readback.get('request'),read_completion=readback.get('completion'))
        if row['id'] in locators or row['id'] != 'p'+str(row['request']['packet_index']):
            raise ValueError('補抽列的 Packet 身分不符')
        selected = locators[row['id']] = {}
        for name,event in events.items():
            if event is None or event['direction']=='UNKNOWN':
                continue
            index = event['packet_index']
            if type(index) is not int or not 0 <= index < count:
                raise ValueError('補抽 Packet 超出案件範圍')
            fields = {key for ref in event['evidence'] for key in ref['fields']}
            if not {'packet_index','direction'} <= fields:
                continue
            timed = event['time_ns'] is not None and 'time_ns' in fields
            selected[name] = dict(binding,packet_index=index,display_level=0,
                                  timestamp={'value':event['time_ns'],'unit':'ns'} if timed else None,
                                  time_display=event['time_display'],channel=event['direction'],direction=event['direction'])
    return locators


class Tool:
    def __init__(self, output, worker_factory=NativeWorker):
        self.root = Path(output).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        # A new path can remain virtual until it exists (e.g. MSIX AppData
        # redirection). COM runs outside that view and must receive the real path.
        self.root = self.root.resolve(strict=True)
        self.token = secrets.token_urlsafe(32)
        self.worker_factory = worker_factory
        self.worker = None
        self.lock = threading.RLock()
        self.case = None
        self.state = {'phase': 'ready', 'message': '拖入一份 .usb / .pex，或按「匯入 Trace」。', 'busy': False}
        self.thread = None
        self.shutting_down = False
        self.cancel_event = threading.Event()
        self.pending_protocol = None

    def event(self, kind, **data):
        # Session tokens never enter persisted evidence.
        with self.lock:
            with (self.root / 'operations.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                    'event': kind, **data}, ensure_ascii=False) + '\n')

    def update(self, phase, message, **extra):
        with self.lock:
            self.state.update(phase=phase, message=message, **extra)
            atomic_json(self.root / 'status.json', self.public())

    def public(self):
        with self.lock:
            value = copy.deepcopy(self.state)
            value['case_id'] = self.case['id'] if self.case else None
            value['trace_name'] = self.case['name'] if self.case else None
            if self.state['phase'] in ('preparing', 'extracting') or (self.pending_protocol and self.state['phase']=='cleanup_unknown'):
                value['case_id'] = None
                value['trace_name'] = self.state.get('pending_trace_name')
            value['scope'] = self.case['model'].get('scope', '') if self.case else 'USB2 EP0 / USB3 Link・LFPS / PD 協商・VDM；以完成後的範圍狀態為準，無候選不代表 USB PASS。'
            value['analyses'] = self.case['model'].get('analyses', []) if self.case else []
            value['model_revision'] = self.case.get('revision',0) if self.case else 0
            if value['case_id'] and 'config_ur' in self.case:
                value['config_ur'] = dict(self.case['config_ur'])
            return value

    def bind(self, model_path, source, prepared=None):
        model_path, source = Path(model_path).resolve(), Path(source).resolve(strict=True)
        if source.suffix.lower() != '.usb' or not source.is_file():
            raise ValueError('請提供單一 .usb 檔案')
        model = validate_model(json.loads(model_path.read_text(encoding='utf-8-sig')))
        before = snapshot(source)
        if before['sha256'] != model['trace_sha256']:
            raise ValueError('報告與 trace SHA-256 不符，拒絕定位')
        case_id = uuid.uuid4().hex
        folder = self.root / case_id
        folder.mkdir()
        working = folder / ('triage-' + case_id[:12] + '.usb')
        if prepared:
            prepared = Path(prepared)
            if snapshot(prepared)['sha256'] != before['sha256']:
                raise ValueError('Prepared copy identity mismatch')
            prepared.rename(working)  # Move the one protected copy, do not duplicate the trace.
        else:
            shutil.copy2(source, working)
        working.chmod(stat.S_IREAD)
        bound = snapshot(working)
        if bound['sha256'] != before['sha256'] or snapshot(source) != before:
            raise ValueError('Trace integrity failed during binding')
        (folder / 'inspection.json').write_bytes(model_path.read_bytes())
        (folder / 'report.html').write_text(self.render(model), encoding='utf-8')
        case = {'id': case_id, 'name': source.name, 'source': source, 'working': working,
                'before': before, 'working_before': bound, 'model': model, 'folder': folder}
        atomic_json(folder / 'binding-evidence.json', {'case_id': case_id, 'source': str(source),
                    'working': str(working), 'source_before': before, 'working_before': bound,
                    'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest()})
        with self.lock:
            self.case = case
        return case

    def integrity(self):
        if not self.case:
            return
        case = self.case
        ok = snapshot(case['source']) == case['before'] and snapshot(case['working']) == case['working_before']
        atomic_json(case['folder'] / 'integrity.json', {'source_and_working_unchanged': ok,
                    'source': snapshot(case['source']), 'working': snapshot(case['working'])})
        if not ok:
            raise ValueError('來源或唯讀副本已變更，已停止定位')

    def load_report(self, model, source):
        self.bind(model, source)
        self.update('report', '報告已載入。選擇候選後可在 LeCroy 定位。', busy=False)

    @staticmethod
    def render(model):
        if model.get('format') == 'pcie-triage-inspection/v1':
            import pcie_workspace
            return pcie_workspace.render(model)
        return presentation.render(model) if model.get('format') == presentation.FORMAT else engine.render(model)

    def navigate(self, case_id, rank, target_index=0, item_kind='candidate'):
        with self.lock:
            if self.shutting_down or self.state['busy']:
                return False
            if self.state['phase'] in ('unresponsive', 'cleanup_unknown'):
                raise ValueError('先完成目前工作清理，再重試')
            if not self.case or case_id != self.case['id'] or type(rank) is not int:
                raise ValueError('工作階段已變更')
            if item_kind not in ('candidate','observation','flow'):raise ValueError('Unsupported navigation item')
            cards = self.case['model'].get('flow_items',[]) if item_kind=='flow' else self.case['model'].get('observations',[]) if item_kind=='observation' else self.case['model']['candidates']
            if rank < 1 or rank > len(cards):
                raise ValueError('候選不存在')
            card = cards[rank - 1]
            choices = presentation.targets(card)
            if type(target_index) is not int or not 0 <= target_index < len(choices):
                raise ValueError('定位目標不存在')
            target = choices[target_index]
            transfer = target if 'native_targets' in card else target['index']
            self.update('navigating', f'正在定位 {presentation.location(target)}…', busy=True, last_navigation=None)
            self.thread = threading.Thread(target=self._navigate, args=(case_id, transfer), daemon=True)
            self.thread.start()
            return True

    def _navigate(self, case_id, transfer):
        if isinstance(transfer, dict) and transfer.get('protocol') == 'PCIe':
            return self._navigate_pcie(case_id, transfer)
        started = time.monotonic()
        self.event('navigation_requested', case_id=case_id, transfer=transfer)
        try:
            self.integrity()
            if self.worker is None:
                if servers():
                    raise RuntimeError('LeCroy 已有工作階段；尚未證明可隔離共存。保留原工作，請關閉本次定位或稍後重試。')
                case = self.case
                binding = {'working_path': str(case['working']), 'trace_sha256': case['before']['sha256']}
                if case['model'].get('format') == presentation.FORMAT:
                    binding['targets'] = [t for c in case['model']['candidates']+case['model'].get('observations',[]) for t in presentation.targets(c)]
                else:
                    binding['transfers'] = [c['transfer_indices'][0] for c in case['model']['candidates']]
                self.worker = self.worker_factory(case['folder'] / ('navigation-' + uuid.uuid4().hex[:8]), binding)
            result = self.worker.request('goto', transfer)
            self.integrity()
            elapsed = round((time.monotonic() - started) * 1000)
            self.event('navigation_result', **{**result, 'case_id': case_id, 'transfer': transfer, 'controller_elapsed_ms': elapsed})
            if result.get('state') != 'api_returned':
                detail = result.get('error', '定位未成功')
                if 'Native session changed' in detail:
                    raise RuntimeError('LeCroy 工作階段已變更或結束，已停止定位。請先按「結束定位工作」再重試。')
                raise RuntimeError('定位未完成，請先結束本次定位再重試。詳細原因：' + detail)
            target = transfer if isinstance(transfer, dict) else presentation.target('USB2', 3, transfer)
            view = {0: 'PKT', 1: 'TRA', 3: 'XFR'}[target['level']]
            self.update('api_returned', f'定位請求已送至 LeCroy：{presentation.location(target)}。請切至 {view} 顯示並核對同一份 Trace、編號、時間與 channel／角色；API 返回不代表畫面已確認。',
                        busy=False, last_navigation={**result, 'controller_elapsed_ms': elapsed})
        except TimeoutError as ex:
            self.event('navigation_timeout', transfer=transfer)
            self.update('unresponsive', str(ex), busy=False)
        except Exception as ex:
            self.event('navigation_error', transfer=transfer, error=str(ex))
            self.update('error', str(ex), busy=False)

    def _navigate_pcie(self, case_id, target):
        import pcie_navigation_service as native
        started=time.monotonic()
        try:
            if not self.case or case_id!=self.case['id']:raise ValueError('工作階段已變更')
            self.integrity();case=self.case;model=case['model']
            if model['native_navigation']=='unavailable':raise ValueError('原生 Packet 範圍尚未核實，不能自動開啟定位')
            if self.worker is None:
                anchors = {loc['packet_index']: loc for card in model['candidates']+model.get('observations',[])+model.get('flow_items',[])
                           for loc in card.get('navigation_locators',[card['locator']])}
                for choices in case.get('config_ur_locators', {}).values():
                    for anchor in choices.values():
                        anchors.setdefault(anchor['packet_index'], anchor)
                binding=dict(request=dict(schema='pcie.navigation-probe/v1',
                    source_trace=dict(path=str(case['source']),sha256=model['source_trace_sha256']),
                    display_trace=dict(path=str(case['working']),sha256=model['display_trace_sha256']),
                    anchors=list(anchors.values())),packet_count=model['coverage']['native_packet_count'])
                self.worker=native.Worker(case['folder']/('navigation-'+uuid.uuid4().hex[:8]),binding)
            result=self.worker.request('goto',target)
            self.integrity()
            self.event('pcie_navigation_result',case_id=case_id,target=target,result=result,controller_elapsed_ms=round((time.monotonic()-started)*1000))
            if result.get('state')=='viewport_ready':
                self.update('viewport_ready','PETracer 已移至 Packet '+str(target['index'])+'；已核對主視圖起點、選取編號、原生時間與方向。請在原生畫面覆核證據。',busy=False,last_navigation=result)
                return
            if result.get('state')!='manual_ready':raise RuntimeError(result.get('error','PCIe 定位未完成'))
            self.update('manual_ready','已核對副本、Packet 與原生時間／方向。請到 PETracer 按 Ctrl+G，輸入 '+str(target['index'])+'；目前仍是人工 GUI 定位。',
                        busy=False,last_navigation=result)
        except TimeoutError as ex:self.update('unresponsive',str(ex),busy=False)
        except Exception as ex:self.update('error',str(ex),busy=False)

    def close_navigation(self):
        if self.worker:
            pcie=self.case and self.case['model'].get('protocol')=='pcie'
            self.worker.close()
            self.worker = None
            if pcie:
                self.integrity()
                return
            deadline = time.monotonic() + 15
            while servers() and time.monotonic() < deadline:
                time.sleep(.2)
            if servers():
                raise RuntimeError('LeCroy 程序尚未退出，保留工作並停止後續擷取')
        self.integrity()

    def end_navigation(self):
        with self.lock:
            if self.shutting_down or self.state['busy']:
                return False
            self.update('closing', '正在釋放本工具的定位工作…', busy=True)
        def close():
            try:
                self.close_navigation()
                self.update('report', '定位工作已結束，可再次定位或匯入其他 trace。', busy=False)
            except Exception as ex:
                self.update('cleanup_unknown', str(ex), busy=False)
        self.thread = threading.Thread(target=close, daemon=True)
        self.thread.start()
        return True

    def native_command(self, message):
        # stdin is a private native-launcher pipe, never an HTTP file endpoint.
        if not isinstance(message, dict):
            raise ValueError('Unsupported native command')
        if set(message) in ({'action', 'path'}, {'action', 'path', 'input_method'}) and message['action'] == 'import':
            return self.import_trace(message['path'], message.get('input_method', 'native_ipc'))
        if set(message) == {'action', 'case_id', 'rank'} and message['action'] == 'navigate':
            return self.navigate(message['case_id'], message['rank'])
        if set(message) == {'action', 'case_id', 'rank', 'target_index'} and message['action'] == 'navigate':
            return self.navigate(message['case_id'], message['rank'], message['target_index'])
        if set(message) == {'action', 'case_id', 'rank', 'target_index','item_kind'} and message['action'] == 'navigate':
            return self.navigate(message['case_id'],message['rank'],message['target_index'],message['item_kind'])
        if set(message)=={'action','case_id','context'} and message['action']=='context':
            return self.set_context(message['case_id'],message['context'])
        if set(message)=={'action','case_id'} and message['action']=='config_ur_run':
            return self.start_config_ur(message['case_id'])
        if set(message)=={'action','case_id','row_id','target'} and message['action']=='config_ur_navigate':
            return self.navigate_config_ur(message['case_id'],message['row_id'],message['target'])
        if message == {'action': 'end'}:
            return self.end_navigation()
        if message == {'action': 'cancel'}:
            with self.lock:
                if self.state['busy'] and self.pending_protocol=='pcie':
                    self.cancel_event.set()
                    phase = 'config_ur' if self.state['phase'] == 'config_ur' else 'extracting'
                    message = '已要求取消，等待原生呼叫安全結束；尚未取消完成。'
                    if phase == 'config_ur':
                        self.case['config_ur']['message'] = message
                    self.update(phase,message,busy=True)
                    return True
                return False
        raise ValueError('Unsupported native command')

    def start_config_ur(self, case_id):
        with self.lock:
            if self.shutting_down or self.state['busy'] or self.state['phase'] in ('unresponsive','cleanup_unknown'):
                return False
            case = self.case
            if not case or case_id != case['id'] or case['model'].get('protocol') != 'pcie':
                raise ValueError('目前案件沒有可補抽的 PCIe Trace')
            count = case['model']['coverage']['native_packet_count']
            if type(count) is not int or count < 1:
                raise ValueError('原生 Packet 範圍尚未核對')
            self.cancel_event.clear()
            self.pending_protocol = 'pcie'
            message = '正在補抽 PCIe 暫存器與 UR…'
            case['config_ur'] = {'state':'running','message':message}
            self.update('config_ur',message,busy=True,last_navigation=None)
            self.thread = threading.Thread(target=self._analyze_config_ur, args=(case,), daemon=True)
            self.thread.start()
            return True

    def _analyze_config_ur(self, case):
        from pcie_pipeline import CleanupUnknown
        phase = 'report'
        try:
            import pcie_config_ur_acquisition as acquisition
            import pcie_config_ur_analysis as analysis
            import pcie_config_ur_report as report
            import pcie_large_io as large
            try:
                self.close_navigation()
            except Exception as exc:
                raise CleanupUnknown(str(exc)) from exc
            model = case['model']
            binding = {key:model[key] for key in ('source_trace_sha256','display_trace_sha256','packet_namespace')}
            binding.update(analysis_id=case['id'],native_packet_count=model['coverage']['native_packet_count'])
            directory = case['folder']/('config-ur-'+uuid.uuid4().hex)
            directory.mkdir()
            def progress(message):
                with self.lock:
                    if not self.cancel_event.is_set():
                        case['config_ur']['message'] = message
                        self.update('config_ur',message,busy=True)
            with native_exclusive():
                observed = acquisition.run(case['working'],case['folder']/'analysis',directory,binding,self.cancel_event,progress)
            self.integrity()
            if self.cancel_event.is_set():
                raise InterruptedError('已取消補抽分析')
            result = analysis.analyze(observed)
            if result.get('schema') != 'pcie.config-ur-evidence/v1' or any(result[key] != value for key,value in binding.items()):
                raise ValueError('補抽結果的來源與案件不符')
            locators = config_ur_locators(result)
            large.check_disk(directory, 32 * large.MIB)
            large.write_json_bounded(directory/'evidence.json',result,limit=32*large.MIB)
            report.write(directory,result)
            if not (directory/'index.json').is_file():
                raise ValueError('補抽報告索引未完成')
            with self.lock:
                if self.cancel_event.is_set() or self.shutting_down:
                    raise InterruptedError('已取消補抽分析')
                if case is not self.case:
                    raise ValueError('補抽的案件已變更')
                message = '暫存器與 UR 證據已整理，可查看原請求、回覆與回讀。'
                case['config_ur'] = {'state':'ready','index':directory.name+'/index.json','message':message}
                case['config_ur_locators'] = locators
                self.pending_protocol = None
                self.update('report',message,busy=False)
                try:
                    self.event('config_ur_completed',case_id=case['id'],index=case['config_ur']['index'])
                except OSError as exc:
                    print('Unable to log completed Config/UR supplement: '+str(exc),file=sys.stderr)
            return
        except InterruptedError as exc:
            message, state = str(exc), 'cancelled'
        except CleanupUnknown as exc:
            message, state, phase = str(exc), 'error', 'cleanup_unknown'
        except TimeoutError as exc:
            message, state, phase = str(exc), 'error', 'unresponsive'
        except Exception as exc:
            message, state = str(exc), 'error'
        with self.lock:
            self.pending_protocol = None
            if self.case is case:
                case['config_ur'] = {'state':state,'message':message}
                case.pop('config_ur_locators',None)
                self.update(phase,message,busy=False)

    def navigate_config_ur(self, case_id, row_id, target_name):
        with self.lock:
            if self.shutting_down or self.state['busy'] or self.state['phase'] in ('unresponsive','cleanup_unknown'):
                return False
            case = self.case
            if not case or case_id != case['id'] or case.get('config_ur',{}).get('state') != 'ready':
                raise ValueError('補抽結果不屬於目前工作')
            if not isinstance(row_id,str) or not isinstance(target_name,str):
                raise ValueError('補抽定位欄位不符')
            anchor = case['config_ur_locators'].get(row_id,{}).get(target_name)
            if anchor is None:
                raise ValueError('這一列缺少可核對的 Packet 位置')
            index = anchor['packet_index']
            target = dict(protocol='PCIe',level=0,index=index,channel=anchor['channel'])
            self.update('navigating',f'正在定位 PCIe · Packet {index}…',busy=True,last_navigation=None)
            self.thread = threading.Thread(target=self._navigate_pcie,args=(case_id,target),daemon=True)
            self.thread.start()
            return True

    def set_context(self,case_id,context):
        """Optional per-import input; no native acquisition, global defaults or rule edits."""
        import pcie_workspace as view
        with self.lock:
            if self.shutting_down or self.state['busy'] or self.state['phase'] in ('unresponsive','cleanup_unknown'):return False
            if not self.case or case_id!=self.case['id'] or self.case['model'].get('protocol')!='pcie':raise ValueError('工程情境不屬於目前 PCIe 工作')
            self.integrity()
            model=view.with_context(self.case['model'],context)
            html_report,md_report=view.render(model),view.markdown(model)
            import pcie_ui_pages
            page_index=pcie_ui_pages.write(self.case['folder'],model,publish=False)
            for name,text in (('report.html',html_report),('report.md',md_report)):
                target=self.case['folder']/name;temp=target.with_suffix(target.suffix+'.tmp');temp.write_text(text,encoding='utf-8');os.replace(temp,target)
            atomic_json(self.case['folder']/'flow-analysis.json',model['flow_analysis'])
            atomic_json(self.case['folder']/'inspection.json',model)
            pcie_ui_pages.publish_index(self.case['folder'],page_index)
            self.case['model']=model;self.case['revision']=self.case.get('revision',0)+1
            self.event('pcie_context_updated',case_id=case_id,context=context,revision=self.case['revision'])
            self.update('report','工程情境已套用於本次 Trace；觀察資料與 Packet 候選保持不變。',busy=False)
            return True

    def import_trace(self, source, input_method='native_ipc'):
        # Called by CLI/native IPC only; never an HTTP path endpoint.
        with self.lock:
            if self.shutting_down or self.state['busy'] or self.state['phase'] in ('unresponsive', 'cleanup_unknown'):
                return False
            source = Path(source).resolve(strict=True)
            if source.suffix.lower() not in ('.usb','.pex') or not source.is_file():
                raise ValueError('一次只接受一份可讀取的 .usb 或 .pex 檔案')
            if input_method not in ('native_ipc', 'drag_drop', 'file_picker'):
                raise ValueError('Unsupported native input method')
            self.event('import_requested', input_method=input_method, source_name=source.name)
            self.cancel_event.clear()
            self.pending_protocol='pcie' if source.suffix.lower()=='.pex' else 'usb'
            self.update('preparing', '準備唯讀副本與擷取…', busy=True, pending_trace_name=source.name, last_navigation=None)
            self.thread = threading.Thread(target=self._analyze, args=(source,), daemon=True)
            self.thread.start()
            return True

    def _analyze(self, source):
        try:
            self.close_navigation()
        except Exception as ex:
            self.update('cleanup_unknown', str(ex), busy=False)
            return
        self.case=None
        try:
            with native_exclusive():
                # The old binding is no longer actionable, even if the new import fails.
                if source.suffix.lower()=='.pex':self._analyze_pcie(source)
                else:self._analyze_exclusive(source)
        except Exception as ex:
            self.update('error', str(ex), busy=False)

    def _analyze_pcie(self,source):
        import pcie_pipeline as pipeline
        import pcie_workspace as view
        case_id=uuid.uuid4().hex;folder=self.root/case_id
        started=time.monotonic()
        try:
            before=snapshot(source,cancel=self.cancel_event)
            result=pipeline.run(source,folder/'analysis',case_id,
                                lambda text:self.update('extracting',text,busy=True),cancel=self.cancel_event,
                                cache_root=self.root.parent/'pcie-conversion-cache')
            model=result['model'];working=result['working']
            if (snapshot(source)!=before or model['source_trace_sha256']!=before['sha256']
                    or snapshot(working)['sha256']!=model['display_trace_sha256']):
                raise ValueError('來源或副本完整性不符')
            atomic_json(folder/'inspection.json',model)
            import pcie_ui_pages
            page_index=pcie_ui_pages.write(folder,model,publish=False)
            if model.get('flow_analysis'):atomic_json(folder/'flow-analysis.json',model['flow_analysis'])
            (folder/'report.html').write_text(view.render(model),encoding='utf-8')
            (folder/'report.md').write_text(view.markdown(model),encoding='utf-8')
            atomic_json(folder/'controller-timing.json',dict(import_to_publication_seconds=time.monotonic()-started,
                pipeline_seconds=result['elapsed_seconds'],ui_interactive='AWAIT_DESKTOP_LOAD'))
            working_before=snapshot(working)
            with self.lock:
                if self.cancel_event.is_set():raise pipeline.Cancelled('已取消報告發布；本次結果未使用，原生清理已確認。')
                pcie_ui_pages.publish_index(folder,page_index)
                self.case=dict(id=case_id,name=source.name,source=source,working=working,before=before,
                    working_before=working_before,model=model,folder=folder)
                try:
                    self.update('report','PCIe 分析結束；先核對流程階段與下一步，次要交易觀察保留原始順序。無候選不代表 PCIe PASS。',busy=False)
                except Exception:
                    self.case=None
                    (folder/'ui-index.json').unlink(missing_ok=True)
                    raise
                try:
                    self.event('pcie_analysis_completed',case_id=case_id,elapsed_seconds=result['elapsed_seconds'],candidate_count=model['candidate_count_total'])
                except OSError as ex:
                    print('Unable to log completed PCIe analysis: '+str(ex),file=sys.stderr)
        except (pipeline.Cancelled,InterruptedError) as ex:self.update('cancelled',str(ex),busy=False)
        except pipeline.Partial as ex:self.update('partial',str(ex)+'；部分擷取已保留，未產生候選。',busy=False)
        except pipeline.CleanupUnknown as ex:self.update('cleanup_unknown',str(ex),busy=False)
        except TimeoutError as ex:self.update('unresponsive',str(ex),busy=False)
        except Exception as ex:
            self.event('analysis_error',error=str(ex));self.update('error',str(ex),busy=False)
        finally:self.pending_protocol=None

    def _analyze_exclusive(self, source):
        import usb_triage_pipeline as pipeline
        started=time.monotonic()
        try:
            if servers():raise RuntimeError('已有 LeCroy 工作階段，受限模式不接管；請保留原工作並稍後重試。')
            self.case=None
            output=self.root/('analysis-'+uuid.uuid4().hex)
            result=pipeline.run(source,output,lambda text:self.update('extracting',text,busy=True))
            self.bind(result['model'],source,result['working'])
            self.event('analysis_completed',elapsed_ms=round((time.monotonic()-started)*1000))
            self.update('report','分析結束。請依左側協定狀態查看候選、缺漏與分析範圍；無候選不代表 USB PASS。',busy=False)
        except subprocess.TimeoutExpired:
            self.update('unresponsive','原生擷取超過等待時間；結果未知，尚未取消呼叫。請先確認原生程序與工作日誌。',busy=False)
        except Exception as ex:
            self.event('analysis_error',error=str(ex));self.update('error',str(ex),busy=False)

    def page(self):
        with self.lock:
            case = self.case
            if not case:
                body = '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>USB Trace Triage</title><main><h1>USB Trace Triage</h1><p>請把一份 .usb 拖入 Windows 工具入口，或按「選擇檔案」。</p></main></html>'
            else:
                model = case['model']
                body = self.render(model)
                scope = model.get('scope', 'USB2 標準 EP0 控制傳輸；未涵蓋 USB3 Link、Bulk、Interrupt、PD。無候選不等於 USB PASS。')
                # Legacy scope may be terse; keep its historical exclusion text.
                if model.get('format') != presentation.FORMAT:
                    scope = 'USB2 標準 EP0 控制傳輸；未涵蓋 USB3 Link、Bulk、Interrupt、PD。無候選不等於 USB PASS。'
                identity = f'<section class="tool-meta"><strong>{html.escape(case["name"])}</strong><br>SHA-256 {model["trace_sha256"][:16]} · {html.escape(model["rule_version"])}<br>找到 {model["episode_count"]} 個待檢查區段；顯示 {len(model["candidates"])} 個，另 {model["omitted_episodes"]} 個未顯示。<p>{html.escape(scope)}</p></section>'
                body = body.replace('</header>', identity + '</header>')
                for c in model['candidates']:
                    marker = f'<article class="card" id="candidate-{c["rank"]}">'
                    body = body.replace(marker, marker + f'<button class="goto" data-rank="{c["rank"]}">在 LeCroy 定位 · {html.escape(presentation.location(presentation.targets(c)[0]))}</button>')
            boot = json.dumps({'token': self.token, 'case_id': case['id'] if case else None})
            extra = '<style>.tool-bar,.tool-meta{padding:16px;background:#e7eff6;border-radius:8px;margin:12px 0}.tool-bar{position:sticky;top:0;z-index:2}.goto{font-size:16px;min-height:44px;background:#244e70;color:white}button:disabled{opacity:.5}#tool-status{white-space:pre-wrap}body{font-family:system-ui,"Microsoft JhengHei",sans-serif}</style>'
            extra += '<section class="tool-bar"><strong>本機工具 · 受限共存模式</strong><p id="tool-status" role="status" aria-live="polite"></p><button id="reload">重新載入結果</button><button id="end-session">結束定位工作</button></section>'
            extra += '<script id="tool-boot" type="application/json">' + boot + '</script><script src="/tool.js" defer></script>'
            body = body.replace('<main>', '<main>' + extra, 1)
            return body


class Handler(BaseHTTPRequestHandler):
    server_version = 'TraceTriage/0.1'
    def log_message(self, *_):
        pass

    def reply(self, status, value, mime='application/json; charset=utf-8'):
        data = value.encode('utf-8') if isinstance(value, str) else json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def authorized(self, mutation=False):
        if self.headers.get('Host') != self.server.authority:
            return False
        if mutation and self.headers.get('Origin') != self.server.origin:
            return False
        return secrets.compare_digest(self.headers.get('X-Trace-Session', ''), self.server.tool.token)

    def do_GET(self):
        if self.headers.get('Host') != self.server.authority or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self.reply(403, {'error': 'Host/source rejected'})
        if self.path == '/':
            return self.reply(200, self.server.tool.page(), 'text/html; charset=utf-8')
        if self.path == '/tool.js':
            return self.reply(200, (HERE / 'usb-control-tool.js').read_text(encoding='utf-8'), 'application/javascript; charset=utf-8')
        if self.path == '/status' and self.authorized():
            return self.reply(200, self.server.tool.public())
        return self.reply(404, {'error': 'Not available'})

    def do_POST(self):
        if not self.authorized(mutation=True):
            return self.reply(403, {'error': '來源或工作階段已失效'})
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 2048 or self.headers.get('Content-Type') != 'application/json':
                return self.reply(400, {'error': 'JSON request required'})
            data = json.loads(self.rfile.read(length))
            if self.path == '/navigate' and set(data) == {'case_id', 'rank'}:
                ok = self.server.tool.navigate(data['case_id'], data['rank'])
                return self.reply(202 if ok else 409, {'accepted': ok})
            if self.path == '/end' and data == {}:
                tool = self.server.tool
                ok = tool.end_navigation()
                return self.reply(202 if ok else 409, {'accepted': ok})
            return self.reply(400, {'error': 'Unsupported action'})
        except (ValueError, TypeError, KeyError) as ex:
            return self.reply(400, {'error': str(ex)})

    do_OPTIONS = lambda self: self.reply(403, {'error': 'Cross-origin control disabled'})


def serve(tool):
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    http.daemon_threads = True
    http.tool = tool
    http.authority = f'127.0.0.1:{http.server_port}'
    http.origin = 'http://' + http.authority
    threading.Thread(target=http.serve_forever, daemon=True).start()
    return http


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--trace', type=Path)
    ap.add_argument('--native-ipc', action='store_true')
    ap.add_argument('--no-browser', action='store_true')
    args = ap.parse_args()
    if os.name != 'nt':
        ap.error('Windows and installed LeCroy are required')
    tool = Tool(args.output)
    if args.report:
        if not args.trace:
            ap.error('--report requires --trace')
        tool.load_report(args.report, args.trace)
    http = serve(tool)
    atomic_json(tool.root / 'endpoint.json', {'url': http.origin, 'controller_pid': os.getpid()})
    print(json.dumps({'url': http.origin}, ensure_ascii=False), flush=True)
    if not args.no_browser:
        webbrowser.open(http.origin)
    try:
        if args.native_ipc:
            # Match the native launcher's wire encoding independently of locale
            # and the embedded interpreter's environment/isolation settings.
            sys.stdin.reconfigure(encoding='utf-8', errors='strict')
            for line in sys.stdin:
                try:
                    message = json.loads(line)
                    if message == {'action': 'close'}:
                        break
                    tool.native_command(message)
                except Exception as ex:
                    tool.update('error', str(ex), busy=False)
        else:
            while True:
                time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        tool.shutting_down = True
        if tool.thread and tool.thread.is_alive():
            supplement = tool.state['phase'] == 'config_ur'
            if supplement:
                tool.cancel_event.set()
            tool.thread.join(timeout=45 if supplement else 15)
        try:
            if tool.thread and tool.thread.is_alive():
                raise RuntimeError('原生操作仍在進行，不得當作已取消或清理完成')
            tool.close_navigation()
            tool.update('closed', '工作已結束', busy=False)
        except Exception as ex:
            tool.update('cleanup_unknown', str(ex), busy=False)
        http.shutdown()
        http.server_close()


if __name__ == '__main__':
    main()
