# PCIe-G3c-0 Message Field Probe — Evidence (2026-09-14)

Status: **PASS** — VSE exposes `in.MessageCode` and `in.MessageRoute` for the
Message TLPs of 1350, and the GUI-checked message reads ERR_COR routed to the
Root Complex. G3a/G3b were not changed. No message is interpreted as a cause of
any candidate; ground truth remains UNKNOWN.

## Inputs

| Item | Identity |
| --- | --- |
| Source trace | `S0-Remove SD7-1350.pex`, SHA-256 `1ADB98F89C2C0CF2A9733EA01552E39438483C4A9741136DC4BE36F0A27F1AEB` |
| Working copy | `C:\Users\reiko\AppData\Local\Temp\pcie-g3c0-20260914-ac855f0d\S0-Remove SD7-1350.pex`, identical identity, ReadOnly |
| Analyzer | PETracer 13.26 (Build 43) BETA, SHA-256 `160A542BF369701DF00466E744C9981FA9C530265AC237D81C0343C8F732E118` |
| Script | `scripts/pcie/g3c0-msg-fields.pevs`, repo and deployed SHA-256 `9389D6E2EE5A876D9A17576FD9F2A17F7220D62B58D7FA0DABDD7C95227B9B48` |
| Name source | `Scripts/VFScripts/VS_constants.inc`, SHA-256 `799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D` (`TLP_MSGCODE_ERR_COR = 0x30`, `TLP_MSGROUTE_TOROOTCOMPLEX = 0x0`, `TLP_MSGCODE_SLOTPOWERLIMIT = 0x50`, `TLP_MSGROUTE_LOCALTERMRECEIVER = 0x4`) |
| References | G1a log SHA-256 `C1B551461F30FD5FE863DE8BF0B95DE68F7028A6972DDCA0F1DDE99E14A17A39`; G2a fields.json SHA-256 `FA64728D3023DF8C476FE858B3C39568E04D3313714EDCED944BEF0FC9D5BB79` |

Field names `in.MessageCode` and `in.MessageRoute` follow installed vendor
verification scripts. Values are emitted as raw hex; names are applied offline.

## Execution

Same guarded GUI sequence as G2a, first attempt succeeded: 13:49:17 loaded,
description verified, 13:49:26.070 Run requested, DONE observed 0.6 s later,
13:49:29 log saved, 13:49:45 PETracer exited.

## Output

Log `artifacts/evidence/pcie-g3c0-20260914/g3c0-msg-fields.log.txt`, 927 bytes,
SHA-256 `FB1A2B1D32F74DABB0BE66CA5D96955E1448D1384D54255976C12309A73F3F8F`:

```text
PCIE_G3C0_MSG_FIELDS_V1 fields=requester_id,message_code,message_route
PCIE_G3C0_MSG|1944516| 4.848 sec|Downstream|0xE|0x0000|0x50|0x4
PCIE_G3C0_MSG|1945029| 4.853 sec|Upstream|0xD|0x0100|0x30|0x0
PCIE_G3C0_MSG|2093072| 5.880 sec|Upstream|0xD|0x0100|0x30|0x0
PCIE_G3C0_END|tlps=938|messages=3|reason=trace_end
------- D O N E !!! -------
```

`verify_g3c0_messages.py` returned `PASS_MESSAGE_FIELD_PROBE_OUTPUT`: END reports
938 TLPs (equal to G1a), and the three message rows equal the G2a message rows
in packet index, display time, channel, type code and RequesterId.
messages.json SHA-256 `08A7307F029E2BB55EC9419EE694ED97EAA1518112AC1C9E288E2AE9D57E1754`.

| Packet | Time | Channel | Type | RequesterId | MessageCode | MessageRoute | GUI |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1944516 | 4.848 sec | Downstream | MsgD (`0xE`) | 000:00.0 | `0x50` SLOTPOWERLIMIT | `0x4` LOCALTERMRECEIVER | not checked for message code |
| 1945029 | 4.853 sec | Upstream | Msg (`0xD`) | 001:00.0 | `0x30` ERR_COR | `0x0` TOROOTCOMPLEX | **MATCHED**: Split view Link Tra 33 shows Msg, Msg Routing To RC, RequesterID 001:0:0, Message Code ERR_COR, explicit ACK #1945030 (`artifacts/evidence/pcie-g2b-20260914/gui-split/split-view-pkt-1945000.png`, SHA-256 `21C3BC2C159504AA024057CC70C9321F2DE2C82D810F4C1DDF9B66344FA06466`) |
| 2093072 | 5.880 sec | Upstream | Msg (`0xD`) | 001:00.0 | `0x30` ERR_COR | `0x0` TOROOTCOMPLEX | not GUI-checked |

## Descriptive observations (not findings)

- Both ERR_COR messages come from RequesterId 001:00.0, the same ID that is the
  CompleterId of the UR completions.
- 1945029 (4.853 sec) follows the first UR group (completions 1945008-1945023);
  2093072 (5.880 sec) sits inside the second UR group (between request 2093071
  and its UR completion 2093075).
- These are temporal adjacencies only. Causality between any UR completion and
  an ERR_COR message is NOT ESTABLISHED; relating them is the scope of G3c.

## Post-close integrity (13:50:07 +08:00, PETracer not running)

Source trace, working copy (ReadOnly), PETracer executable and repo/deployed
probe script retained the identities above.

## Limits

- One trace; only one message GUI-checked for its code.
- Message payload/header fields beyond code and routing were not read.
