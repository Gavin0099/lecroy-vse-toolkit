# Review cases

1. USB2 `Completed=0`, GET_DESCRIPTOR accepted, no retained DATA: use
   `usb2-control.json`; inspect the first transfer's response/status and capture
   tail. Use `usb2-enumeration.json` only to request verified descriptor bytes,
   reset epoch and configuration evidence. No firmware fault or invalid
   descriptor follows from missing data. A legal short reply is a counterexample.
2. USB3 Wake/Reset without later retained LGOOD: use `usb3-link-ltssm.json` and
   `usb3-recovery.json`. Request actual state, direction, mode, channel, epoch
   and capture continuity. An anchor is not U0; ordinary power-state recovery
   is a counterexample to treating every Recovery as failure.
3. PD Request/Accept/Request: use `pd-negotiation.json`. Ask for scoped
   Source_Capabilities/PDO/RDO/PS_RDY and roles. Do not call it a failed power
   contract from header/group data alone. Request/Accept/PS_RDY is still not
   voltage measurement. EPR/PPS and unrecognized revisions remain unevaluated.
4. PD VDM NAK/BUSY: use `pd-vdm.json`. Bind SOP/channel/sender/epoch, SVID,
   command, structured version and object position before comparison. Different
   SOP, command or reset epoch must not be merged. One allowed NAK is neutral;
   an Enter Mode ACK does not demonstrate working display output.
5. Missing sources, altered card pins or a scope belonging to another trace:
   preserve the native observations, request evidence and decline a bound
   technical instruction. A catalog URL alone cannot repair the missing support.
