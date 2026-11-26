# Independent fixture expectations

- Owner contract: one trace; no label/marker/known-time input; four required card
  fields; no candidate is not PASS; repeated requests do not fill all ranks.
- LeCroy VSE manual PDF 89 and installed VSTools.inc: native fields and bounded
  payload access. Real replay shows SETUP-prefixed payload; handwritten fixture
  bytes do not use the production serializer to create expected response lengths.
- `80 06 00 01 00 00 12 00` requests an 18-byte device descriptor. A matching
  26-byte native payload contains eight SETUP bytes and 18 response bytes.
- [Descriptor explanation](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-descriptors)
  and [configuration layout](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbspec/ns-usbspec-_usb_configuration_descriptor):
  declared type/length and wTotalLength support bounded content inspection.
  An eight-byte header probe or a complete short string is not a fault by itself.
- Handwritten configuration/BOS headers test larger followup reads against actual
  declared length. Different descriptor indices cannot inherit support evidence.
- Observed address assignment or successful same-request response breaks an
  episode. Relative-delay fixtures use one second, unrelated to real fail times;
  the comparison is a heuristic, not a USB timeout limit.
- CSV blank fields remain None, not zero/success. Marker mutation does not change
  discovery. Source identity/count/ordering/prefix failures reject the input.
- Renderer tests check escaping/scope/copyable coordinates; actual browser checks
  separately verify rendering, expansion, empty state and copying.
