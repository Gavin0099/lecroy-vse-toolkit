"""Build an explicit Windows portable trial ZIP; never include captures."""
import argparse
import ast
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
         'tools/usb_triage_model.py',
         'tools/usb_debug_knowledge.py', 'docs/usb-knowledge-contract.md',
         'tools/usb_triage_pipeline.py', 'tools/usb3_triage.py',
         'tools/run-usb-triage-data.ps1', 'scripts/usb3-triage-data.vse',
         'tools/pd_triage.py', 'tools/run-pd-triage-data.ps1', 'scripts/pd-triage-headers.vse',
         'docs/usb3-pd-tool-usage.md',
         'scripts/usb-control-transfers.vse']

PYTHON_VERSION = '3.13.16'
PYTHON_SHA256 = '97dae5274cc54867065e8d5a3226e48c35017ed332a0fdb0e27d5b5821961297'
PYWIN32_SHA256 = '718a38f7e5b058e76aee1c56ddd06908116d35147e133427e59a3983f703a20d'


def pcie_sources():
    """Package the local static dependency closure, never frozen case outputs."""
    pending=['pcie_workspace','pcie_pipeline','pcie_navigation_service','pcie_ui_pages']
    found={}
    while pending:
        name=pending.pop()
        if name in found:continue
        path=next((d/(name+'.py') for d in (ROOT/'tools',ROOT/'scripts/pcie') if (d/(name+'.py')).is_file()),None)
        if path is None:continue
        found[name]=path.relative_to(ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Import):pending.extend(n.name.split('.')[0] for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:pending.append(node.module.split('.')[0])
    return sorted(found.values())+['scripts/pcie/'+n for n in
        ('g1a-tlp-count.pevs','g1c-tlp-rows-all.pevs','g2a-tlp-fields.pevs','g3c0-msg-fields.pevs',
         'g1c-tlp-rows-batched.pevs','g2a-tlp-fields-batched.pevs','g3c0-msg-fields-batched.pevs',
         'vopt-phase-scan.pevs','vopt-transactions.pevs')]


FILES=list(dict.fromkeys(FILES+pcie_sources()+['docs/pcie-workflow-parity-matrix.md',
    'docs/usb-pcie-tool-usage.md','docs/pcie-large-trace-safeguards-usage.md','docs/pcie-dense-analysis-usage.md','docs/pcie-dense-analysis-contract-20261020.md','docs/pcie-parity-engineer-trial.md','tools/pcie-gui-navigation.cs',
    'docs/pcie-flow-triage-contract.md','docs/pcie-knowledge-sources.md','docs/pcie-engineer-ux-contract-20261021.md',
    'knowledge/pcie/LICENSE-NOTICE.md','knowledge/pcie/sources.json','knowledge/pcie/rule-cards.schema.json',
    'knowledge/pcie/next-actions.json','knowledge/pcie/next-action-contract.md',
    '.agents/skills/pcie-debug-analysis/SKILL.md','.agents/skills/pcie-debug-analysis/references/examples.md',
    '.agents/skills/pcie-debug-analysis/agents/openai.yaml']+
    [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'knowledge/pcie/cards').glob('*.json'))]))

FILES += [p.relative_to(ROOT).as_posix() for directory in
          (ROOT/'knowledge/usb', ROOT/'.agents/skills/usb-debug-analysis')
          for p in sorted(directory.rglob('*')) if p.is_file() and
          p.suffix in ('.json', '.md', '.yaml')]


def com_runtime_files(wheel):
    if hashlib.sha256(Path(wheel).read_bytes()).hexdigest()!=PYWIN32_SHA256:
        raise ValueError('pywin32 wheel differs from pinned cp313 Windows x64 release')
    data={}
    with zipfile.ZipFile(wheel) as archive:
        if archive.testzip() is not None:raise ValueError('pywin32 wheel CRC failed')
        for name in archive.namelist():
            if name.endswith('/') or '..' in Path(name).parts:continue
            if name.startswith('pywin32_system32/') and name.endswith('.dll'):
                data['runtime/'+Path(name).name]=archive.read(name)
            elif (name=='pythoncom.py' or name.startswith(('win32/','win32com/','pywin32-311.dist-info/'))):
                data['runtime/'+name]=archive.read(name)
    data['runtime/python313._pth']=b'python313.zip\n.\nwin32\nwin32/lib\n..\\tools\n..\\scripts\\pcie\n# Isolated; no installed Python or user site.\n'
    return data


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


def build(output, runtime_zip=None, pywin32_wheel=None):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {name: (ROOT / name).read_bytes() for name in FILES}
    if runtime_zip:
        if not pywin32_wheel:raise ValueError('PCIe portable build requires pinned --pywin32-wheel')
        data.update(runtime_files(runtime_zip))
        data.update(com_runtime_files(pywin32_wheel))
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
        helper=staging/'PcieGuiNavigation.exe'
        framework=compiler.parent
        subprocess.run([str(compiler),'/nologo','/target:exe','/out:'+str(helper),
                        '/reference:'+str(framework/'WPF/UIAutomationClient.dll'),
                        '/reference:'+str(framework/'WPF/UIAutomationTypes.dll'),
                        '/reference:'+str(framework/'WPF/WindowsBase.dll'),
                        '/reference:System.Web.Extensions.dll',str(ROOT/'tools/pcie-gui-navigation.cs')],
                       check=True,capture_output=True,timeout=60)
        data['tools/PcieGuiNavigation.exe']=helper.read_bytes()
        data['USBTraceTriage.exe.config'] = b'<?xml version="1.0"?><configuration><startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.8"/></startup></configuration>'
    manifest = {'kind': 'portable-windows-x64-trial-candidate' if runtime_zip else 'source-only-windows-trial-candidate',
                'version': 'usb-pcie-navigation-reliability-candidate-20261021-r7.6.1',
                'pywin32': {'version':'311','wheel_sha256':PYWIN32_SHA256} if runtime_zip else None,
                'python': {'version': PYTHON_VERSION, 'archive_sha256': PYTHON_SHA256,
                           'source': 'https://www.python.org/downloads/release/python-31316/',
                           'license': 'runtime/LICENSE.txt', 'path_config': 'isolated; tools only'} if runtime_zip else None,
                'not_qualified': ['1 GiB+ native trace capacity', '2 GiB native analysis', 'candidate graphs or indexed outputs above documented safety budgets',
                                  'cross-segment semantic equivalence', 'full analysis cache', 'clean Windows', 'physical drag-drop', 'engineer usability',
                                  'LeCroy 10.50 runtime', 'unseen-case correctness and time saving', 'safe multi-instance coexistence',
                                  'other PETracer versions', 'full-trace PCIe coverage',
                                  'physical link pairing and bidirectional L0', 'LTSSM Flow Graph ignore-setting equivalence',
                                  'complete native Split child-packet mapping',
                                  'normative PCI-SIG conformance', 'Flit flow analysis', 'engineer context applicability beyond explicit scope',
                                  'USB normative conformance', 'exact USB3 LTSSM state extraction',
                                  'full PD payload, PPS/EPR/role-swap qualification', 'implicit USB Skill selection by a fresh model session'],
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
    parser.add_argument('--pywin32-wheel',type=Path,help='Pinned pywin32 311 cp313 Windows x64 wheel')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output, args.runtime_zip, args.pywin32_wheel), ensure_ascii=False))
    except subprocess.CalledProcessError as ex:
        raise RuntimeError(ex.stdout.decode(errors='replace') + ex.stderr.decode(errors='replace')) from ex
