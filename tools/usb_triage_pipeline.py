"""One protected copy, sequential existing USB2 and USB3 acquisition paths."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import usb_control_app as host
import usb3_triage as usb3
import pd_triage as pd
import usb_triage_model as view

HERE=Path(__file__).resolve().parent


def failed(protocol,scope,error):
    return dict(protocol=protocol,state='failed',scope=scope,coverage={},episode_count=0,candidates=[],
                limitations=['本協定分析未完成：'+str(error)])


def usb2_analysis(m):
    host.validate_model(m)
    coverage=m['coverage']
    cards=copy.deepcopy(m['candidates'])
    for c in cards:c['native_targets']=[view.target('USB2',3,c['transfer_indices'][0],c['start_ns'])]
    return dict(protocol='USB2',state='partial' if coverage['truncated'] else 'analyzed' if coverage['eligible_controls'] else 'not_observed',
                scope=m['scope'],rule_version=m['rule_version'],coverage=coverage,limitations=m['limitations'],episode_count=m['episode_count'],candidates=cards)


def command(args, output, stage, progress, resources):
    if host.servers():raise RuntimeError('LeCroy 尚有工作，未接管或重送擷取。')
    progress(stage)
    with (output/'analysis.log').open('ab') as log:
        p=subprocess.Popen([host.POWERSHELL,'-NoProfile','-MTA','-File',*args],stdin=subprocess.DEVNULL,
                           stdout=log,stderr=subprocess.STDOUT,env=host.powershell_environment(),
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        host.atomic_json(output/'active-acquisition.json',dict(pid=p.pid,stage=stage,started_utc=time.time()))
        deadline=time.monotonic()+600
        while p.poll() is None:
            host.sample_resources(output,p.pid,resources)
            if time.monotonic()>deadline:
                # Timeout does not cancel COM or kill the native server.
                raise subprocess.TimeoutExpired(p.args,600)
            time.sleep(1)
    deadline=time.monotonic()+15
    while host.servers() and time.monotonic()<deadline:time.sleep(.2)
    if host.servers():raise RuntimeError('原生程序清理未確認，停止後續擷取。')
    return p.returncode


def run(source,output,progress=lambda message:None):
    source=Path(source).resolve(strict=True);output=Path(output)
    if source.suffix.lower()!='.usb' or not source.is_file():raise ValueError('Expected one .usb trace')
    output.mkdir(parents=True,exist_ok=False);output=output.resolve(strict=True)
    before=host.snapshot(source);work=output/'working.usb'
    shutil.copy2(source,work);work.chmod(stat.S_IREAD);protected=host.snapshot(work)
    if before['sha256']!=protected['sha256']:raise ValueError('Protected copy hash mismatch')
    host.atomic_json(output/'source-before.json',dict(source=str(source),snapshot=before,working=protected))
    resources=dict(process_peaks={},sampled_workdir_peak_bytes=0,sample_interval_seconds=1,
                   limitations='Observed process-lifetime peaks and sampled disk use; not summed simultaneous peaks.')
    analyses=[];data=None;started=time.monotonic()
    def intact():
        if host.snapshot(source)!=before or host.snapshot(work)!=protected:
            raise ValueError('來源或唯讀副本已變更，停止所有分析。')
    try:
        code=command([str(HERE/'run-usb-control-triage.ps1'),'-TracePath',str(work),'-Output',str(output/'usb2'),
                      '-Python',sys.executable,'-UseReadOnlyInput'],output,'正在分析 USB2 EP0…',progress,resources)
        intact()
        try:
            if code:raise ValueError('USB2 runner failed; see usb2/raw-result.json and analysis.log')
            m=json.loads((output/'usb2/inspection.json').read_text(encoding='utf-8-sig'))
            if m['trace_sha256']!=before['sha256']:raise ValueError('USB2 trace identity mismatch')
            analyses.append(usb2_analysis(m))
        except (ValueError,OSError,KeyError) as ex:analyses.append(failed('USB2','USB2 standard EP0',ex))
        code=command([str(HERE/'run-usb-triage-data.ps1'),'-TracePath',str(work),'-Output',str(output/'usb3')],
                     output,'正在分析 USB3 Link／LFPS 與協定可見範圍…',progress,resources)
        intact()
        try:
            if code:raise ValueError('USB3 runner failed; see usb3/raw-result.json and analysis.log')
            data=usb3.normalize(json.loads((output/'usb3/raw-result.json').read_text(encoding='utf-8-sig')))
            if data['trace_sha256']!=before['sha256']:raise ValueError('USB3 trace identity mismatch')
            host.atomic_json(output/'usb3/data.json',data)
            analyses.append(usb3.discover(data))
        except (ValueError,OSError,KeyError) as ex:analyses.append(failed('USB3','USB3 Link / LFPS',ex))
        pd_count=data['coverage']['pd_packet_events'] if data else None
        if pd_count==0:
            analyses.append(dict(protocol='PD',state='not_observed',coverage={'pd_packet_events':0},scope='未觀察到 PD；不以 CC 事件代替 PD 訊息',episode_count=0,candidates=[],limitations=['未觀察到 PD 不代表 USB PASS。']))
        else:
            code=command([str(HERE/'run-pd-triage-data.ps1'),'-TracePath',str(work),'-Output',str(output/'pd')],
                         output,'正在分析 PD 原生群組與協商／VDM 證據…',progress,resources)
            intact()
            try:
                if code:raise ValueError('PD runner failed; see pd/raw-result.json and analysis.log')
                pd_data=pd.load(output/'pd')
                if pd_data['trace_sha256']!=before['sha256']:raise ValueError('PD trace identity mismatch')
                host.atomic_json(output/'pd/data.json',pd_data)
                analyses.append(pd.discover(pd_data))
            except (ValueError,OSError,KeyError) as ex:analyses.append(failed('PD','PD 基本協商 / VDM',ex))
        model=view.compose(before['sha256'],analyses)
        host.atomic_json(output/'inspection.json',model)
        (output/'report.html').write_text(view.render(model),encoding='utf-8')
        return dict(output=output,model=output/'inspection.json',working=work)
    finally:
        unchanged=host.snapshot(source)==before and host.snapshot(work)==protected
        host.atomic_json(output/'integrity.json',dict(source_unchanged=host.snapshot(source)==before,
                         working_unchanged=host.snapshot(work)==protected,readonly=not bool(work.stat().st_mode&stat.S_IWRITE)))
        resources['analysis_elapsed_ms']=round((time.monotonic()-started)*1000)
        host.atomic_json(output/'resources.json',resources)
        if not unchanged:raise ValueError('Trace integrity failed; result cannot be trusted')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with host.native_exclusive():r=run(a.trace,a.output,lambda text:print(text,flush=True))
    print(json.dumps({k:str(v) for k,v in r.items()},ensure_ascii=False))
