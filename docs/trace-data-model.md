# Trace data model

This document separates the first observable summary from future normalized data. It is intentionally not a complete USB schema.

## M1 summary fields

The first script writes these groups of fields:

```text
trace_name
trace_start_time
trace_end_time
delivered_event_count
first_delivered_event_time
last_delivered_event_time
first_delivered_event
last_delivered_event
protocol._USB2_channels
protocol._USB3_channels
protocol._USB_PD_channels
protocol._USB_CC_channels
protocol.other
channel._USB2
channel._USB2_1
channel._USB2_2
channel._USB2_3
channel._USB3_RX
channel._USB3_TX
channel._USB_PD_0
channel._USB_CC_0
channel.other
level._PKT
level._TRA
level._XFER
level._SPL_TRA
level._SCSI
level._PHY_TRA
level.other
```

`delivered_event_count` means callback invocations observed by this script. The protocol buckets are aggregates derived from the observed channel buckets, not independent decoder metadata. The channel buckets are coarse observations based on the channel identifiers exposed by VSE. The level buckets reflect the explicit M1 level selection. They are not yet a protocol-decoder completeness claim.

## Future packet record

M2 may introduce a bounded record with fields such as:

```text
index, timestamp, channel, level, event, address, endpoint,
direction, packet_type, length, error, raw_data
```

Each field must first be confirmed as exposed by the relevant LeCroy event context. Missing fields stay absent or explicitly unknown; they are not reconstructed from guesses.

## Future transfer record

M3 may group already-decoded packets into transactions and transfers. The grouping rules and replay fixtures must be specified after M2 field evidence exists.
