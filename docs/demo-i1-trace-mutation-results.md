# DEMO-I1: PASS trace mutation localization

## Scope

This probe compares the pristine PASS `.usb` extracted from the Desktop zip
with the PASS sacrificial copy after the already completed combined Demo
extractor run. It does not rerun VSE and does not interpret the changed bytes.

Tool: `tools/localize-trace-mutation.ps1`.

## Result

- Before size: `159,435,991`
- After size: `159,436,011`
- Size delta: `+20` bytes
- First differing offset: `441` (`0x1B9`)
- Last differing offset: `159,436,010` (`0x9813E2A`)
- Changed byte positions: `307`
- Changed ranges: `15` disjoint ranges
- Appended range: offsets `159,435,991`-`159,436,010` (`20` bytes)
- Appended before hex: empty
- Appended after hex: `6F74206F7220466F726365205472696700000000`

The mutation is not append-only. The file grew by `20` bytes, but the binary
comparison also found changed bytes in existing content. The earliest changed
position is offset `441`; the latest changed position is in the appended tail.

The changed ranges are:

```text
441
453
667
669
1101
1371
2159
2161
2554-2555
133356886-133357013
159435817
159435841-159435870
159435872-159435933
159435935-159435990
159435991-159436010  (appended 20 bytes)
```

Representative observed byte changes include `12 -> 40` at offset `441`,
`48 -> A5` at offset `453`, and the appended tail
`6F74206F7220466F726365205472696700000000`. The full bounded before/after
hex report is retained in the external JSON result produced by the localizer.
This localizes the mutation scope but does not establish its semantic meaning
or show that it is safe to ignore.

## Claim boundary

The result does not prove that the changed bytes are harmless metadata,
persistent decoding data, or a normal LeCroy behavior. It also does not prove
that all traces would receive the same mutation. A read-only or immutable-input
probe is still a separate follow-up and has not been run here.
