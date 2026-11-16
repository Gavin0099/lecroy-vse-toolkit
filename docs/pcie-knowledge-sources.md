# PCIe knowledge sources — 2026-10-20

The machine-readable source manifest is `knowledge/pcie/sources.json`; cards are authored engineering notes, not imported source code or specifications. Exact upstream commits, source/README/license hashes and lookup evidence are recorded in `artifacts/evidence/pcie-flow-spec-20261020/upstream-pins.json`.

| Source | Local use | Boundary |
|---|---|---|
| [Xilinx PCIe Debug K-Map](https://github.com/Xilinx/pcie-debug-kmap) | Training and enumeration debug questions, MIT project | FPGA-specific timing and settings are not universal PCIe requirements |
| [Linux pci_regs.h](https://github.com/torvalds/linux/blob/master/include/uapi/linux/pci_regs.h) | Register reference and vocabulary cross-check | GPL-2.0 WITH Linux-syscall-note; no copied header/code |
| [Linux pciehp_ctrl.c](https://github.com/torvalds/linux/blob/master/drivers/pci/hotplug/pciehp_ctrl.c) | Link-up and device configuration are separate operations | GPL-2.0-or-later; no copied implementation |
| [pciutils](https://github.com/pciutils/pciutils) | Config/capability decoding reference | GPL-2.0-or-later; no copied implementation or dependency |
| [cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie) | Independent SC/UR/CRS/CA fixture values and counterexamples | MIT model is not normative conformance authority; no runtime dependency |
| [LeCroy VSE manual](https://cdn.teledynelecroy.com/files/manuals/petracer_vse_manual.pdf) | Typed event and native field meanings | Current PDF 13.42 differs from local 13.26.0.43; native receipts decide local capability |
| [PCI-SIG specifications policy](https://pcisig.com/specifications) | Identify acquisition/AI-use restrictions | No restricted specification ingested; no normative mismatch classification enabled |

P0 cards cover Link/LTSSM, Hot Plug, enumeration and Completion. P1 DLLP/Replay and ASPM cards supply only questions and required evidence. The loader rejects unknown/mismatched pins, missing fields and any attempted upgrade to `SPEC_MISMATCH_CONFIRMED`. `FLIT` is explicitly unsupported for this analysis; unknown capture mode never becomes conformance PASS.

Completion values (0 SC, 1 UR, 2 CRS, 4 CA) remain observations. Same Requester/Tag in the opposite direction is a limited association hint. Complete Split mapping, device identity, retry/replay mechanism, normative timeout and successful initialization remain unestablished unless separate evidence supports them.

No remote lookups or AI calls occur in the packaged analysis runtime. Source links can be read by the engineer separately. A changed knowledge pack changes its hash; the same sealed trace inputs and pack reproduce the same flow model.

The authored `next-action-contract.md` is the authoritative local policy for per-action provenance. It is explicitly not a specification. `next-actions.json` maps each Flow action and each card's next check to a reviewed source locator, revision, conditions, required evidence and limitations. `sources.json` records reviewed action locators; the local contract also has a content hash. A reference match is an offline consistency check, not a new remote-source or hardware qualification.

Missing/mismatched/inapplicable support becomes an evidence request with NOT_EVALUATED. Generic card guidance is unbound until trace/phase evidence is supplied. BIOS-specific logging instructions have been removed; optional platform evidence is requested under local policy. ASPM remains a request for applicable vendor policy/effective-time/target evidence, with no inferred acceptance criteria.

The single maintained Codex entry is `.agents/skills/pcie-debug-analysis/`. Historical r7 reports and the frozen r7 ZIP record the former `skills/` location; they are not rewritten as proof that discovery succeeded.
