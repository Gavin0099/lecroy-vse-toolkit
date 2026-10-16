"""Build an explicit Windows portable trial ZIP; never include captures."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ['Start-USB-Trace-Triage.cmd', 'docs/usb-control-tool.md',
         'tools/start-usb-control-tool.ps1', 'tools/usb-control-entry.cs',
         'tools/usb-control-startup.cs', 'tools/usb-control-theme.cs',
         'tools/usb_control_app.py', 'tools/usb-control-tool.js',
         'tools/usb-control-navigation.ps1', 'tools/usb-control-navigation.cs',
         'tools/run-usb-control-triage.ps1', 'tools/u01-selection-host.cs',
         'tools/usb_control_triage.py', 'tools/usb_control_automation.py',
         'scripts/usb-control-transfers.vse']

PYTHON_VERSION = '3.13.16'
PYTHON_SHA256 = '97dae5274cc54867065e8d5a3226e48c35017ed332a0fdb0e27d5b5821961297'


def runtime_files(runtime_zip):
    runtime_zip = Path(runtime_zip)
    if hashlib.sha256(runtime_zip.read_bytes()).hexdigest() != PYTHON_SHA256:
        raise ValueError('Python archive SHA-256 differs from the official release')
    with zipfile.ZipFile(runtime_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError('Python ZIP CRC failed')
        data = {}
        for name in archive.namelist():
            if '/' in name or '\\' in name or name in ('.', '..'):
                raise ValueError('Unexpected embedded runtime path')
            body = archive.read(name)
            if name == 'python313._pth':
                body = b'python313.zip\n.\n..\\tools\n# Isolated runtime; no user site or installed Python.\n'
            data['runtime/' + name] = body
    for required in ('python.exe', 'python313.dll', 'python313.zip', 'python313._pth', 'LICENSE.txt'):
        if 'runtime/' + required not in data:
            raise ValueError('Missing runtime file: ' + required)
    return data


def build(output, runtime_zip=None):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {name: (ROOT / name).read_bytes() for name in FILES}
    if runtime_zip:
        data.update(runtime_files(runtime_zip))
        staging = Path(tempfile.mkdtemp(prefix='portable-build-', dir=output.parent))
        compiler = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        target = staging / 'USBTraceTriage.exe'
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu',
                        '/main:TraceToolEntry', '/out:' + str(target),
                        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
                        '/reference:System.Web.Extensions.dll', '/reference:System.Core.dll',
                        *[str(ROOT / 'tools' / name) for name in
                          ('usb-control-entry.cs', 'usb-control-startup.cs', 'usb-control-theme.cs')]],
                       check=True, capture_output=True, timeout=60)
        data['USBTraceTriage.exe'] = target.read_bytes()
        data['USBTraceTriage.exe.config'] = b'<?xml version="1.0"?><configuration><startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.8"/></startup></configuration>'
    manifest = {'kind': 'portable-windows-x64-trial-candidate' if runtime_zip else 'source-only-windows-trial-candidate',
                'version': 'tool03-portable-20261016',
                'python': {'version': PYTHON_VERSION, 'archive_sha256': PYTHON_SHA256,
                           'source': 'https://www.python.org/downloads/release/python-31316/',
                           'license': 'runtime/LICENSE.txt', 'path_config': 'isolated; tools only'} if runtime_zip else None,
                'not_qualified': ['clean Windows', 'physical drag-drop', 'engineer usability',
                                  'LeCroy 10.50 runtime', 'unseen-case correctness and time saving', 'safe multi-instance coexistence'],
                'files': {name: {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
                          for name, body in data.items()}}
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, body in data.items():
            archive.writestr('USB-Trace-Triage/' + name, body)
        archive.writestr('USB-Trace-Triage/manifest.json',
                         json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for name, body in data.items():
            if archive.read('USB-Trace-Triage/' + name) != body:
                raise ValueError('Packaged bytes changed: ' + name)
    return {'zip': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'bytes': output.stat().st_size, 'files': len(data), 'verification': 'CRC and exact bytes passed'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--runtime-zip', type=Path, help='Official pinned Python embeddable x64 ZIP')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output, args.runtime_zip), ensure_ascii=False))
    except subprocess.CalledProcessError as ex:
        raise RuntimeError(ex.stdout.decode(errors='replace') + ex.stderr.decode(errors='replace')) from ex
