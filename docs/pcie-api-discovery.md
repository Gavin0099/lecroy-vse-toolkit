# PCIe document-backed discovery draft

Historical draft: its P0 labels and installation status below describe September
11. P0-A subsequently passed on September 12. The revised slice definitions in
[PLAN](../PLAN.md) supersede this draft's roadmap; the script remains unexecuted
and is not the minimal C1 script or authorization for runtime/COM work.

2026-09-11: owner authorized reading specifications and preparing code while
installation continues. This relaxes the implementation ordering, not the real
trace acceptance gates. P0-B is a draft; P0-A/B/C are not PASS.

## Official references

- [PCIe VSE reference](https://cdn.teledynelecroy.com/files/manuals/petracer_vse_manual.pdf):
  cover identifies PCIe Protocol Analysis 13.38, generated 2026-08-12.
- [PCIe Automation API](https://cdn.teledynelecroy.com/files/manuals/pcieautomationmanual.pdf):
  `IPETraceForScript::RunVerificationScript`, printed pages 331-334.

The online VSE version differs from the previously observed download listing
(13.36). Installed documentation and includes must be checked after installation.
No vendor includes or manuals are copied into the repository.

## API-to-code review map

Page numbers below are printed manual pages, not PDF viewer indexes.

| Decision | VSE reference |
| --- | --- |
| Native `.pevs` extension; module metadata and `VSTools.inc` | section 2, pp. 2-3 |
| Start/event/finish callbacks | section 3, p. 5 |
| Index, level, channel, event code and `Time2` components | section 5.1, p. 12 |
| Payload byte count and numeric TLP type | sections 5.2.1/5.2.3, pp. 13/18 |
| TLP-only selection at packet level, both directions | sections 7.1, 8.1, 8.7, 8.10 |
| Output formatting and informational script mode | sections 14.1-14.2, 20.2, 21.1 |
| Segment identity | section 15.5 |

## Draft behavior

[`hello-events.pevs`](../scripts/pcie/hello-events.pevs) samples the first five
TLP callbacks. It continues traversal and separately reports observed target
callbacks and emitted records. This is deliberately not a complete extractor.
It emits JSON-shaped lines to the VSE output window; durable export is unproven.
The GUI may add presentation markup, so copied output needs inspection.

Time is preserved as three integer components with explicit scales. The
picosecond component describes API representation; actual capture resolution
is unknown. No floating-point seconds or derived enum labels are introduced.

`probe_finish_callback` means only that callback was reached. It never claims
execution SUCCESS, a complete trace, a device PASS, or count reconciliation.
Zero sampled records cannot yet distinguish absent TLPs from a runtime problem.
An absent finish record must not be promoted to success. P0-D's four outcomes
still require real completion/error evidence and independently exercised tests.

## Automation finding and boundary

The official API documents `CATC.PETracer`, `OpenFile`, and
`RunVerificationScript`, including an absolute script path. Its return enum
distinguishes license failure (-3), still running (-2), missing script (-1),
verification failed (0), passed (1), and informational DONE (2).

This establishes a documented programmatic candidate, not an installed bridge.
The VSE manual also documents `NotifyClient` (section 18.1) and file output;
GUI discovery therefore does not need a host first. No host is created in this
slice. Informational DONE alone is not sufficient extraction acceptance.

## Validation completed and outstanding

- Source reviewed against the API map; only documented PCIe members selected.
- JSON format strings checked offline with synthetic numeric substitutions,
  including nonzero picoseconds and a nanosecond boundary; this checks text
  shape only, not CSL formatting/runtime behavior or event truth.
- No installed PCIe compiler/parser, includes or real runtime was available
  for verification. Syntax acceptance, field availability and GUI output are
  explicitly unverified. There is no emulated-VSE PASS claim.

After installation, first verify executable/build, installed includes, and
the field declarations above. Then create and fingerprint a separate read-only
working copy using the setup policy. Load the native `.pevs` through the
installed VSE UI (manual section 4); confirm selection and output settings.
Do not open an original capture for this step.

Compare at least three emitted events against the GUI by segment/index,
direction, raw type, payload length and exact time components. Record original
output and the application result. Check source and working-copy integrity.
If no TLP exists, report that observation and revisit event selection; do not
invent values or infer a PCIe failure. No runtime steps were executed here.
