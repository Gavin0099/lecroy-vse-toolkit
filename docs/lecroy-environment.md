# LeCroy environment

## Observed local installation

The current development machine exposes:

```yaml
application: Teledyne LeCroy USB Protocol Suite
executable: "C:\\Program Files\\LeCroy\\USB Protocol Suite\\UsbSuite.exe"
version: "10.40 (Build 6309)"
vendor_script_root: "C:\\Users\\Public\\Documents\\LeCroy\\USB Protocol Suite\\Scripts\\VFScripts"
manual_staging_workspace: "C:\\Users\\reiko\\Desktop\\Lecory"
```

The script root contains the installed `VSTools.inc`, constants, template, and official examples. These files are local reference material and are not copied into this repository.

The Desktop workspace exists separately from the repo and currently contains two external `.usb` trace directories. Keep any temporary VSE script copy in a dedicated child directory rather than beside the trace directories. Trace binaries remain external inputs and are not committed.

## M1 setup checklist

1. Confirm the application version and trace type.
2. Open a known trace in USB Protocol Suite.
3. Load `scripts/hello/trace-info.vse` directly, or copy it into a dedicated script subdirectory under `C:\Users\reiko\Desktop\Lecory` if the GUI workflow needs a staging directory.
4. Confirm that `%include "VSTools.inc"` resolves to the installed vendor script root.
5. Run the script without changing decoder assignments during the first probe.
6. Preserve the generated summary and the application-reported result as external test evidence.

## Handling boundary

Trace captures can contain proprietary traffic, device identifiers, payloads, or large binary data. Keep them outside Git by default. Add a trace to the repository only after confirming that its license, sensitivity, and size are appropriate.
