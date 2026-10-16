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


def snapshot(path):
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
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
    os.replace(temp, path)


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
        atomic_json(self.root / 'request.json', {'id': identity, 'action': action, 'transfer': transfer})
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
        self.state = {'phase': 'ready', 'message': '拖入一份 .usb，或按「匯入 Trace」。', 'busy': False}
        self.thread = None
        self.shutting_down = False

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
            if self.state['phase'] in ('preparing', 'extracting'):
                value['case_id'] = None
                value['trace_name'] = self.state.get('pending_trace_name')
            value['scope'] = 'USB2 標準 EP0 控制傳輸；未涵蓋 USB3 Link、Bulk、Interrupt、PD。無候選不等於 USB PASS。'
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
        (folder / 'report.html').write_text(engine.render(model), encoding='utf-8')
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

    def navigate(self, case_id, rank):
        with self.lock:
            if self.shutting_down or self.state['busy']:
                return False
            if self.state['phase'] in ('unresponsive', 'cleanup_unknown'):
                raise ValueError('先完成目前工作清理，再重試')
            if not self.case or case_id != self.case['id'] or type(rank) is not int:
                raise ValueError('工作階段已變更')
            cards = self.case['model']['candidates']
            if rank < 1 or rank > len(cards):
                raise ValueError('候選不存在')
            transfer = cards[rank - 1]['transfer_indices'][0]
            self.update('navigating', f'正在定位 Transfer {transfer}…', busy=True, last_navigation=None)
            self.thread = threading.Thread(target=self._navigate, args=(case_id, transfer), daemon=True)
            self.thread.start()
            return True

    def _navigate(self, case_id, transfer):
        started = time.monotonic()
        self.event('navigation_requested', case_id=case_id, transfer=transfer)
        try:
            self.integrity()
            if self.worker is None:
                if servers():
                    raise RuntimeError('LeCroy 已有工作階段；尚未證明可隔離共存。保留原工作，請關閉本次定位或稍後重試。')
                case = self.case
                self.worker = self.worker_factory(case['folder'] / ('navigation-' + uuid.uuid4().hex[:8]),
                    {'working_path': str(case['working']), 'transfers': [c['transfer_indices'][0] for c in case['model']['candidates']]})
            result = self.worker.request('goto', transfer)
            self.integrity()
            elapsed = round((time.monotonic() - started) * 1000)
            self.event('navigation_result', **{**result, 'case_id': case_id, 'transfer': transfer, 'controller_elapsed_ms': elapsed})
            if result.get('state') != 'api_returned':
                detail = result.get('error', '定位未成功')
                if 'Native session changed' in detail:
                    raise RuntimeError('LeCroy 工作階段已變更或結束，已停止定位。請先按「結束定位工作」再重試。')
                raise RuntimeError('定位未完成，請先結束本次定位再重試。詳細原因：' + detail)
            self.update('api_returned', f'定位請求已送至 LeCroy：Transfer {transfer}。請核對 Trace、時間與 Address/EP；必要時切換 LeCroy 視窗。',
                        busy=False, last_navigation={**result, 'controller_elapsed_ms': elapsed})
        except TimeoutError as ex:
            self.event('navigation_timeout', transfer=transfer)
            self.update('unresponsive', str(ex), busy=False)
        except Exception as ex:
            self.event('navigation_error', transfer=transfer, error=str(ex))
            self.update('error', str(ex), busy=False)

    def close_navigation(self):
        if self.worker:
            self.worker.close()
            self.worker = None
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
        if message == {'action': 'end'}:
            return self.end_navigation()
        raise ValueError('Unsupported native command')

    def import_trace(self, source, input_method='native_ipc'):
        # Called by CLI/native IPC only; never an HTTP path endpoint.
        with self.lock:
            if self.shutting_down or self.state['busy'] or self.state['phase'] in ('unresponsive', 'cleanup_unknown'):
                return False
            source = Path(source).resolve(strict=True)
            if source.suffix.lower() != '.usb' or not source.is_file():
                raise ValueError('一次只接受一份可讀取的 .usb 檔案')
            if input_method not in ('native_ipc', 'drag_drop', 'file_picker'):
                raise ValueError('Unsupported native input method')
            self.event('import_requested', input_method=input_method, source_name=source.name)
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
        try:
            with native_exclusive():
                self._analyze_exclusive(source)
        except Exception as ex:
            self.update('error', str(ex), busy=False)

    def _analyze_exclusive(self, source):
        started = time.monotonic()
        try:
            if servers():
                raise RuntimeError('已有 LeCroy 工作階段，受限模式不接管；請保留原工作並稍後重試。')
            self.case = None
            output = self.root / ('analysis-' + uuid.uuid4().hex)
            self.update('extracting', 'LeCroy 正在讀取／擷取 USB2 EP0；仍可查看狀態。', busy=True)
            with (self.root / 'analysis.log').open('ab') as log:
                # Acquisition uses the synchronous host's MTA path, separate
                # from pumped STA navigation. Never inherit the native IPC stdin
                # pipe: PowerShell/native Python must not consume that stream.
                proc = subprocess.Popen([POWERSHELL, '-NoProfile', '-MTA', '-File', str(HERE / 'run-usb-control-triage.ps1'),
                                         '-TracePath', str(source), '-Output', str(output), '-Python', sys.executable],
                                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW, env=powershell_environment())
                self.analysis_process = proc
                resources = {'process_peaks': {}, 'sampled_workdir_peak_bytes': 0, 'sample_interval_seconds': 1,
                             'limitations': 'Observed process lifetime peaks; controller may include previous jobs. Disk maximum is sampled. Peaks are not summed or treated as simultaneous.'}
                deadline = time.monotonic() + 600
                while proc.poll() is None:
                    sample_resources(output, proc.pid, resources)
                    if time.monotonic() > deadline:
                        raise subprocess.TimeoutExpired(proc.args, 600)
                    time.sleep(1)
                code = proc.returncode
                if output.exists():
                    atomic_json(output / 'resources.json', resources)
            deadline = time.monotonic() + 15
            while servers() and time.monotonic() < deadline:
                time.sleep(.2)
            if code or servers():
                raise RuntimeError('擷取失敗或原生程序清理未完成；請查看 analysis.log 與 PowerShell／LeCroy 環境。')
            self.bind(output / 'inspection.json', source, output / 'working.usb')
            resources['analysis_elapsed_ms'] = round((time.monotonic() - started) * 1000)
            resources['retained_analysis_directory_bytes'] = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
            atomic_json(output / 'resources.json', resources)
            self.event('analysis_completed', elapsed_ms=round((time.monotonic() - started) * 1000))
            self.update('report', ('分析完成。請先看主要候選，並在 LeCroy 核對。' if self.case['model']['candidates'] else '本次 USB2 EP0 分析未找到足夠候選；不代表 USB PASS。'), busy=False)
        except subprocess.TimeoutExpired:
            self.update('unresponsive', '原生擷取超過等待時間；結果未知。尚未取消呼叫，請先完成清理。', busy=False)
        except Exception as ex:
            self.event('analysis_error', error=str(ex))
            self.update('error', str(ex), busy=False)

    def page(self):
        with self.lock:
            case = self.case
            if not case:
                body = '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>USB Trace Triage</title><main><h1>USB Trace Triage</h1><p>請把一份 .usb 拖入 Windows 工具入口，或按「選擇檔案」。</p></main></html>'
            else:
                model = case['model']
                body = engine.render(model)
                identity = f'<section class="tool-meta"><strong>{html.escape(case["name"])}</strong><br>SHA-256 {model["trace_sha256"][:16]} · {html.escape(model["rule_version"])} · VSE<br>找到 {model["episode_count"]} 個待檢查區段；顯示 {len(model["candidates"])} 個，另 {model["omitted_episodes"]} 個未顯示。<p>USB2 標準 EP0 控制傳輸；未涵蓋 USB3 Link、Bulk、Interrupt、PD。無候選不等於 USB PASS。</p></section>'
                body = body.replace('</header>', identity + '</header>')
                for c in model['candidates']:
                    marker = f'<article class="card" id="candidate-{c["rank"]}">'
                    body = body.replace(marker, marker + f'<button class="goto" data-rank="{c["rank"]}">在 LeCroy 定位 · Transfer {c["transfer_indices"][0]}</button>')
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
            tool.thread.join(timeout=15)
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
