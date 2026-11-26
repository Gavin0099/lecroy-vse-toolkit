# Three review examples (synthetic, not new native evidence)

## Expected Hot Plug

Scope: one source/display/namespace, channel 1 Upstream, epoch 2, Packet 100–140. Engineer note explicitly expects a device switch in that interval. Packet 110 is Link Down; Packet 135 has valid directional L0.

Output: Link Down is an expected-context observation only inside that range. L0 is observed. Next check is same-link post-L0 Config/Completion and OS enumeration evidence. Another channel or epoch remains outside this exemption. Initialization and device identity remain NOT_ESTABLISHED. Local guidance: HOTPLUG-01, LTSSM-01, ENUM-01.

## Unexpected Link issue

Scope: source-bound channel 2 Downstream epoch 4, Packet 200–260. Engineer note says no unplug was expected. Link Down and subsequent Recovery are observed; no later valid L0 is retained.

Output: check the disconnect/retraining interval and operation markers. This is CHECK_RECOMMENDED, not a proven timeout. Unknown capture tail, filters and physical link mapping prevent a claim that recovery definitively failed. A later invalid LTSSM does not inherit an earlier L0. Local guidance: LTSSM-01, HOTPLUG-01.

## Post-L0 initialization unknown

Scope: one imported trace with no context. Upstream L0 is retained at Packet 500. Config requests at 410 and 415 precede it; same association key alone does not establish retry. A later SC/CRS/UR/CA must retain its actual status and source.

Output: begin at 500 and look for same-Link/epoch Config/Completion, target BDF and external enumeration logs. Packets 410/415 cannot be used as post-500 failure evidence. Unknown Split mapping means no complete transaction or timeout claim. Do not invent a device name, a Hot Plug intent or a PCI-SIG clause. Local guidance: ENUM-01, CPL-01; DLLP/Replay and ASPM cards remain guidance only.
