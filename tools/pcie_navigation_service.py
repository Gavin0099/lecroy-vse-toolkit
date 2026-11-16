"""Persistent owned PETracer session with verified menu navigation and fallback."""
from __future__ import annotations

import argparse
import gc
from contextlib import contextmanager
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import pcie_navigation_probe as probe
import native_navigation as nav
import pcie_gui_navigation as gui


@contextmanager
def exclusive():
    """Serialize this tool's PCIe workers; never attach to a user's session."""
    import win32event
    import win32api
    handle=win32event.CreateMutex(None,False,r'Local\LeCroyTraceTriage.PCIe')
    acquired=False
    try:
        acquired=win32event.WaitForSingleObject(handle,0) in (0,0x80)
        if not acquired:raise RuntimeError('EXISTING_SESSION_BLOCKED: another PCIe worker owns the session')
        yield
    finally:
        if acquired:win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


def verify_export(text, work, anchor, native_ns):
    """Independent native text verifies the actual file, Packet and direction."""
    file_match=re.search(r'^\s*File (.+)\.\s*$',text,re.M)
    if not file_match or Path(file_match[1]).resolve()!=Path(work).resolve():
        raise ValueError('Native export describes another display file')
    match=re.search(r'Packet\('+str(anchor['packet_index'])+r'\) (Upstream|Downstream)\b([\s\S]*?)(?=Packet\(|\Z)',text)
    if not match:raise ValueError('Native export does not contain requested Packet')
    if anchor['direction']!='UNKNOWN' and match[1]!=anchor['direction']:
        raise ValueError('Native direction differs from candidate')
    timestamp=re.search(r'Time Stamp\(([0-9.]+)s\)',match[2])
    if not timestamp or Decimal(timestamp[1])*1000000000!=Decimal(str(native_ns)):
        raise ValueError('Native text/API timestamp mismatch')
    return dict(direction=match[1],timestamp_ns=native_ns,packet_index=anchor['packet_index'],
                file_verified=True,gui_verified=False)


def validate_binding(binding):
    request=binding['request'];anchors=request.get('anchors')
    if not isinstance(anchors,list) or not anchors:raise ValueError('No candidate locators')
    seen=set()
    for anchor in anchors:
        nav.validate_request(dict(request,anchors=[anchor]))
        nav.validate_index(anchor['packet_index'],binding['packet_count'])
        if anchor['packet_index'] in seen:raise ValueError('Ambiguous duplicate Packet locator')
        seen.add(anchor['packet_index'])
    return request


class Worker:
    def __init__(self,directory,binding):
        self.root=Path(directory);self.root.mkdir()
        probe.write(self.root/'binding.json',dict(binding,controller_pid=os.getpid()))
        self.log=(self.root/'worker.log').open('wb');self.timed_out=False
        self.proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(self.root)],
            stdin=subprocess.DEVNULL,stdout=self.log,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def request(self,action,transfer=None,timeout=90):
        if self.timed_out:raise TimeoutError('原生狀態未知，停止重試；工作副本已保留。')
        deadline=time.monotonic()+timeout;identity=uuid.uuid4().hex
        while not (self.root/'ready.json').exists():
            self._wait(deadline)
        probe.write(self.root/'request.json',dict(id=identity,action=action,target=transfer))
        while True:
            path=self.root/'response.json'
            if path.exists():
                data=json.loads(path.read_text(encoding='utf-8'))
                if data.get('id')==identity:return data
            self._wait(deadline)

    def _wait(self,deadline):
        if self.proc.poll() is not None:
            path=self.root/'session.json'
            receipt=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            raise RuntimeError(receipt.get('error','PCIe worker ended; inspect worker.log'))
        if time.monotonic()>=deadline:
            self.timed_out=True
            self.proc.kill();self.proc.wait(timeout=5)  # Only this Python worker.
            probe.write(self.root/'timeout.json',dict(native_cancelled='UNKNOWN',worker_pid=self.proc.pid))
            raise TimeoutError('PETracer 無回應；已停止工具 worker，未取消或強制終止 PETracer。請先核對原生狀態。')
        time.sleep(.1)

    def close(self,timeout=45):
        try:
            if self.timed_out:raise RuntimeError('Native cleanup UNKNOWN after timeout; working copy retained')
            if self.proc.poll() is None:
                result=self.request('close',timeout=timeout)
                if result.get('state')!='closed':raise RuntimeError(result.get('error','Native cleanup unconfirmed'))
                self.proc.wait(timeout=timeout)
                receipt=json.loads((self.root/'session.json').read_text(encoding='utf-8'))
                if receipt.get('native_cleanup')!='confirmed':raise RuntimeError('PETracer cleanup unconfirmed; working copy retained')
            elif self.proc.returncode:
                path=self.root/'session.json'
                receipt=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                if receipt.get('open_file_count')!=0:
                    raise RuntimeError('Native worker exited abnormally; cleanup unknown')
            else:
                path=self.root/'session.json'
                receipt=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                if receipt.get('native_cleanup')!='confirmed':
                    raise RuntimeError('Native worker exited without confirmed cleanup; working copy retained')
        finally:self.log.close()


def serve(root):
    import pythoncom
    import win32com.client
    import win32api,win32process
    root=Path(root);binding=json.loads((root/'binding.json').read_text(encoding='utf-8'))
    request=validate_binding(binding);nav.verify_files(request)
    work=Path(request['display_trace']['path']).resolve()
    before=nav.identity(work);trace=analyzer=selector=None;created=[];last=None;open_count=0;owner=None
    receipt=dict(state='ready',open_file_count=0,coexistence='RESTRICTED_NO_EXISTING_SESSION',gui_navigation='manual_ctrl_g')
    # A process handle refers to this controller, including after PID reuse.
    parent=win32api.OpenProcess(0x1000,False,binding['controller_pid'])
    pythoncom.CoInitialize()
    def save():probe.write(root/'session.json',receipt)
    def close_owned():
        nonlocal trace,selector,analyzer
        if trace is not None:
            # Close only the IPETrace object opened by this worker, never a process.
            result=nav.invoke(trace,'Close');receipt['close']=result
            if not result['ok']:raise RuntimeError('Owned trace Close failed')
        selector=trace=analyzer=None
        if nav.identity(work)!=before:raise ValueError('Working copy changed')
        nav.verify_files(request)
    try:
        with exclusive():
            probe.write(root/'ready.json',dict(ready=True));save()
            while win32process.GetExitCodeProcess(parent)==259:
                pythoncom.PumpWaitingMessages()
                path=root/'request.json'
                if not path.exists():time.sleep(.1);continue
                command=json.loads(path.read_text(encoding='utf-8'))
                if command['id']==last:time.sleep(.1);continue
                last=command['id'];started=time.monotonic()
                result=dict(id=last,state='failed',gui_navigation='manual_ctrl_g')
                try:
                    if command['action']=='close':
                        close_owned();result['state']='closed'
                    elif command['action']=='goto':
                        nav.verify_files(request)
                        if nav.identity(work)!=before:raise ValueError('Working copy changed')
                        target=command['target'];matches=[a for a in request['anchors'] if a['packet_index']==target.get('index')]
                        if target.get('protocol')!='PCIe' or target.get('level')!=0 or len(matches)!=1:
                            raise ValueError('Candidate target outside current binding')
                        anchor=matches[0];nav.validate_index(anchor['packet_index'],binding['packet_count'])
                        if trace is None:
                            if probe.processes():raise RuntimeError('EXISTING_SESSION_BLOCKED: PETracer 已有工作，工具未接管。請保留原工作並稍後重試。')
                            receipt['capabilities']=probe.capabilities()
                            if probe.processes():raise RuntimeError('EXISTING_SESSION_BLOCKED')
                            analyzer=win32com.client.DispatchEx('CATC.PETracer')
                            created=probe.processes()
                            if len(created)!=1:raise RuntimeError('AMBIGUOUS_OWNERSHIP: no trace opened')
                            owner=gui.process_identity(created[0]);receipt['owner']=owner
                            trace=analyzer.OpenFile(str(work));open_count+=1
                            selector=win32com.client.CastTo(trace,'IPETraceForScript15')
                        if probe.processes()!=created or gui.process_identity(created[0])!=owner:
                            raise RuntimeError('Native session changed; stop and end this navigation session')
                        result['show_window']=nav.invoke(selector,'ShowAppWindow',1)
                        gui.preflight(owner)
                        receipt['native_trace_name']=trace.GetName()
                        count=int(selector.GetPacketsCountEx());nav.validate_index(anchor['packet_index'],count)
                        if count!=binding['packet_count']:raise ValueError('Native count changed')
                        # GetName can be just a basename. The independent native
                        # export supplies the actual full path before selection.
                        exported=root/('packet-'+last+'.txt');trace.ExportToText(str(exported),anchor['packet_index'],anchor['packet_index'])
                        stamp=selector.GetPacketStartTime(0,anchor['packet_index'])
                        verified=verify_export(exported.read_text(encoding='utf-8-sig'),work,anchor,stamp)
                        selected=nav.select_packet(selector,anchor,count)
                        if selected['status']!='SELECTION_VERIFIED' or selected['timestamp_ns']!=stamp:raise ValueError('Native selection not verified: '+selected['status'])
                        result.update(state='manual_ready',selection=selected,native_verified=verified,
                                      manual=nav.manual_instructions(work,anchor),open_file_count=open_count)
                        result['gui_command']=gui.navigate(owner,selector,anchor['packet_index'])
                        if result['gui_command']['status']=='viewport_readback_verified':
                            result.update(state='viewport_ready',gui_navigation='owned_menu_with_readback')
                    else:raise ValueError('Unsupported navigation operation')
                except Exception as exc:
                    result.update(error=str(exc),hresult=getattr(exc,'hresult',None),excepinfo=getattr(exc,'excepinfo',None))
                result['elapsed_ms']=round((time.monotonic()-started)*1000)
                with (root/'operations.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(result,ensure_ascii=False)+'\n')
                receipt.update(result,open_file_count=open_count);save();probe.write(root/'response.json',result)
                if command['action']=='close':return 0 if result['state']=='closed' else 2
    except Exception as exc:
        receipt.update(state='failed',error=str(exc));save()
        return 2
    finally:
        try:close_owned()
        except Exception as exc:receipt['cleanup_error']=str(exc)
        gc.collect();pythoncom.CoUninitialize();win32api.CloseHandle(parent)
        started=time.monotonic()
        while created and any(p in probe.processes() for p in created) and time.monotonic()-started<30:time.sleep(.2)
        receipt['remaining_pids']=probe.processes()
        receipt['cleanup_wait_seconds']=time.monotonic()-started
        receipt['native_cleanup']='confirmed' if not receipt.get('cleanup_error') and not any(p in receipt['remaining_pids'] for p in created) else 'unknown'
        save()
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',required=True,type=Path)
    raise SystemExit(serve(parser.parse_args().worker))
