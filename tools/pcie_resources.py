"""Read-only process-lifetime peak working set; unavailable remains unknown."""
import os
import time


def sample(pid):
    if os.name!='nt':return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
            ('peak_ws','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle:return None
    try:
        value=Counters();value.cb=ctypes.sizeof(value)
        if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(value),value.cb):return None
        return dict(pid=pid,peak_working_set_bytes=int(value.peak_ws),
                    working_set_bytes=int(value.working_set),
                    private_commit_bytes=int(value.pagefile),
                    peak_private_commit_bytes=int(value.peak_pagefile))
    finally:kernel.CloseHandle(handle)


def peak_bytes(pid):
    value=sample(pid)
    return value['peak_working_set_bytes'] if value else None


def timed(receipt, name, function, *args, **kwargs):
    started=time.monotonic()
    try:
        return function(*args,**kwargs)
    finally:
        receipt.setdefault('timings',[]).append(dict(
            stage=name,seconds=time.monotonic()-started))
