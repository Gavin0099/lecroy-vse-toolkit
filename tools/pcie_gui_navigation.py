"""Owned native GUI command with bounded helper lifetime and COM readback."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import subprocess
import time
import native_navigation as nav

def process_identity(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    h=kernel.OpenProcess(0x1000,False,pid)
    if not h:raise OSError('Cannot verify owned process')
    try:
        times=[wintypes.FILETIME() for _ in range(4)];size=wintypes.DWORD(32768);name=ctypes.create_unicode_buffer(size.value)
        if not kernel.GetProcessTimes(h,*[ctypes.byref(t) for t in times]) or not kernel.QueryFullProcessImageNameW(h,0,name,ctypes.byref(size)):raise OSError('Cannot read process identity')
        return dict(pid=pid,created_filetime=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime,executable=name.value)
    finally:kernel.CloseHandle(h)

def navigate(owner,selector,index):
    helper=Path(__file__).resolve().with_name('PcieGuiNavigation.exe')
    result=dict(status='manual_required',gui_verified=False)
    if process_identity(owner['pid'])!=owner:raise RuntimeError('Native process identity changed')
    if not helper.is_file():return dict(result,error='GUI helper unavailable; use Ctrl+G')
    try:
        proc=subprocess.run([str(helper),str(owner['pid']),str(owner['created_filetime']),owner['executable']],
            capture_output=True,text=True,encoding='utf-8',timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        data=json.loads(proc.stdout)
        result['command']=data
        result['helper_diagnostic']=proc.stderr
        if proc.returncode!=0 or data.get('status')!='invoked':return dict(result,error=data.get('error','Native menu unavailable'))
    except (subprocess.TimeoutExpired,ValueError,OSError) as exc:
        diagnostic=getattr(exc,'stderr',None)
        if isinstance(diagnostic,bytes):diagnostic=diagnostic.decode('utf-8',errors='replace')
        return dict(result,error=str(exc),helper_diagnostic=diagnostic)
    deadline=time.monotonic()+3
    while True:
        selected=nav.invoke(selector,'GetSelectedDispUnit');visible=nav.invoke(selector,'GetFirstVisibleDispUnit')
        result.update(selected=selected,first_visible=visible)
        if selected['ok'] and visible['ok'] and list(selected['value'])==[0,index] and list(visible['value'])==[0,index]:
            result['status']='viewport_readback_verified';return result
        if time.monotonic()>=deadline:return dict(result,error='Menu invoked; viewport readback not verified')
        time.sleep(.1)

def preflight(owner):
    helper=Path(__file__).resolve().with_name('PcieGuiNavigation.exe')
    if not helper.is_file():return  # source-only manual fallback
    if process_identity(owner['pid'])!=owner:raise RuntimeError('Native process identity changed')
    try:
        p=subprocess.run([str(helper),str(owner['pid']),str(owner['created_filetime']),owner['executable'],'check'],
            capture_output=True,text=True,encoding='utf-8',timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        result=json.loads(p.stdout)
        if p.returncode!=0 or result.get('status')!='ready':raise ValueError(result.get('error','GUI not ready'))
    except (subprocess.TimeoutExpired,ValueError,OSError) as exc:
        raise RuntimeError('PETracer 視窗尚未就緒；請先關閉本次原生對話框，再重試或使用 Ctrl+G。 '+str(exc)) from exc
