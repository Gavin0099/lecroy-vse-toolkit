# P10 independent expectations

PCI-45 WDK ntddk.h public LinkControl layout reviewed2026-10-13 (page updated
2026-06-29): ASPM bits1:0; CommonClockConfig bit6; ClockPowerManagement bit8.
Only these applicable raw fields are used. LinkDisable/RetrainLink are excluded
because the WDK documents port-type applicability restrictions.

Independent bit examples: 0x42 => ASPM2, CommonClock1, ClockPM0.
0x100 => ASPM0, CommonClock0, ClockPM1. Mask0x3 exposes only ASPM; an
unobserved clock bit remains unknown, not clear. Write intent is never readback.
Queries on a different device, epoch, layout or preceding capability discovery
are ineligible for this bounded case profile.

No assertion of L1 entry, L1SS configuration, clock electrical action, effective
state or Disable-ASPM policy follows from these fields. Expected values are
hand-authored from bit layout/invariants rather than the decoder implementation.
