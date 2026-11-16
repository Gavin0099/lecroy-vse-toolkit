# USB Debug Knowledge contract

USB-SPEC-00–04 extend the existing USB2 EP0, USB3 Link/LFPS and PD native-group
analysis. They do not change candidate discovery, ranking, native navigation or
protocol verdicts. PCIe's knowledge and state machine remain separate.

The six cards are authored engineering review instructions, not executable
USB-IF conformance rules. `knowledge/usb/sources.json` distinguishes official
catalogs, reviewed test documentation, field definitions, implementation
examples and this local engineering contract. A catalog proves availability
and revision only; it cannot support a technical action. Linux code is a field
or implementation reference, not evidence of Windows behavior. No third-party
source code, complete specification, or normative acceptance criteria is bundled.

Each action carries a card ID, directly located source references, an immutable
local pack digest, protocol/revision applicability, required evidence, observed
scope and limitations. A source match is offline pin verification only. Unknown
protocol revision is preserved; an unknown revision cannot enable a
revision-specific action. Missing, mismatched or inapplicable evidence yields
`EVIDENCE_REQUEST` / `NOT_EVALUATED`, never a violation.

Source and display SHA-256, native namespace, target level/index, and the visible
time interval bind even a request for more evidence. USB2 transfer-local review
requires Address/EP; enumeration additionally needs a verified reset epoch and
descriptor bytes. USB3 phase review needs channel, direction, mode, epoch and
actual LTSSM state evidence; an anchor or LGOOD is insufficient. PD review needs
channel, SOP, sender and reset/attach epoch; negotiation content also needs
verified PDO/RDO and role evidence. VDM needs SVID, command, object position and
structured version. No missing scope is inferred from a filename or timestamp.

Existing hint text is preserved as an authored local inspection policy. Source
references explain what fields/stages to inspect; they do not validate the
trace observation or prove a timer, root cause, enumeration, power delivery or
Alt Mode success. A short descriptor reply, NAK, Recovery, Wait, Reject, BUSY,
or expected reset alone is not a fault. Accept/GoodCRC is not PS_RDY or measured
VBUS. Enter Mode ACK is not proof of working video/data. Independently supported
packet errors remain visible in existing analysis.

Knowledge failure is isolated: preserve all protocol results and locators,
label knowledge unavailable, and provide no bound action. First-screen hints
remain the existing candidate's next step; source and evidence details are
available in the limits tab and HTML disclosure. No extra candidate is created.

Validation: six-card shape/pin checks, positive/missing/inapplicable/tampered
source and scope fixtures, saved native USB2/USB3/PD replay with unchanged
discovery results, offline packaged loading and existing USB/PCIe regressions.
Startup discovery, explicit loading and implicit invocation are separate claims;
static validation alone does not qualify a fresh Codex session.
