# P03 fixture oracles

The expected cells below were authored from LC-01 §§5.2.2–3 (installed manual,
PDF pages21–25), not by calling `applicable()` or the script generator.

- ACK native type0: AckNak_SeqNum is applicable; VC_ID/HdrFC/DataFC/scales are
  not applicable. Null applicable members remain unknown, never unsupported.
- UpdateFC_P native type8: credit fields apply; AckNak_SeqNum does not.
- MRd32 native type1: PSN/Length apply; ByteCount/LowerAddr/ComplStatus do not.
- CplD native type18: the three completion fields apply.
- Null is an API observation, not proof that the API lacks support. A zero flag
  is a raw vendor value, not a compliance PASS.
- One callback may produce at most one sample; each known type emits the first
  eight callbacks. Summary denominators must equal actual rows/counts.
- Packet index is zero-based in the converted trace; no namespace substitution,
  negative inference from empty samples, or original12.36 index mapping.

Synthetic raw integers are transport examples, not protocol qualification.
Length zero is preserved; scales stay raw, without capacity conversion.
