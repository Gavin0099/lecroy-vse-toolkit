---
name: usb-debug-analysis
description: Analyze USB2 enumeration and control transfers, USB3 Link/LFPS/recovery, and USB PD negotiation or VDM evidence in lecroy-vse-toolkit. Use for USB trace debugging, unknown initialization, or the next engineering check, including Chinese USB questions. Not for PCIe-only tasks or complete USB compliance certification.
---

# USB evidence review

Use current `PLAN.md`, code and verified acquisition receipts. Paths below are
relative to the repository or portable-package root. This Skill assists Codex;
the desktop engine stays deterministic and offline.

- Read `knowledge/usb/sources.json` and the relevant cards. Validate pins with
  `tools/usb_debug_knowledge.py` (`load()`). Read
  `docs/usb-knowledge-contract.md` for the action/scope contract. The six JSON
  cards are authoritative; do not maintain a second copy inside this Skill.
- Start with `inspection.json`, protocol `data.json`, raw-result and integrity
  receipts. Identify source/display hashes, native level/index, visible time
  range, coverage and truncation. A Transfer number is not a Packet number.
  Never operate raw traces or reuse an unowned LeCroy session.
- USB2: inspect SETUP, optional DATA and STATUS; distinguish actual descriptor
  bytes from native completion flags. Keep Address/EP and reset epoch separate;
  address reuse can refer to another device. NAK, a short read or expected STALL
  alone does not prove a defect or failed enumeration.
- USB3: Link Commands/LFPS can guide a review, but an LTSSM anchor contains no
  exact state. Do not infer U0, a physical port, direction or recovery failure
  from packet speed or absence of later Link Commands. U0 does not establish
  enumeration or usable bulk/stream traffic. USB4 is outside this pack.
- PD: retain SOP versus cable SOP'/SOP'', channel, sender, reset/attach epoch,
  header revision, payload and roles. Accept/GoodCRC does not establish PS_RDY,
  a selected PDO/RDO or measured power. Distinct native groups do not establish
  wire retry counts. VDM ACK/Enter Mode does not establish working Alt Mode;
  examine SVID, structured version, command/object position and later evidence.
- Each recommendation needs a directly supporting source, applicability,
  required evidence and limits. Official catalogs show available revisions,
  not rules. Linux headers/implementations show fields/examples, not Windows
  behavior or USB-IF compliance. Do not copy third-party source or entire specs
  into the repo. Unknown revision/scope, missing or inapplicable support stays
  `EVIDENCE_REQUEST` / `NOT_EVALUATED`; never fabricate a clause or timer.
- Present the last supported observation, what is unverified, a useful next
  check and an exact source-bound native locator. Preserve independently
  supported packet errors. Missing evidence and no candidates do not mean
  USB PASS. API success is separate from verified GUI navigation.

Use [examples](references/examples.md) for positive and counterexample reviews.
Report static validation, real fresh-session discovery, new-trace accuracy and
human time saving separately.
