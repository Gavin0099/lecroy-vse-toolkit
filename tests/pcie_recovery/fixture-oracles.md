# P11 independent fixture basis

LC-01 Packet context documents the raw tuple as state, sub-state, validity,
sub-sub-state. Recovery / Equalization / HotReset / L0 names are engine constants,
not hardware electrical evidence. Fixtures intentionally use synthetic codes
101–105 so hardcoded current engine numbers cannot pass them.

1. Valid Recovery point => positive named state observation, not an entry time.
2. Invalid/ambiguous state tuple => visible raw source, no positive feature.
3. One exact duplicated capture row => one point observation, two source refs.
4. Same packet/channel but conflicting tuples => neither claims a positive state.
5. Consecutive saved samples cannot prove continuously held state or duration.
6. Missing reverse direction / EQ / HotReset / PERST => unknown, never absence.
7. HotReset label may be observed without proving a physical reset.
8. Equalization label with valid Recovery main-state => EQ state point; no PHY result.

Expected outcomes are authored from these evidence invariants, not by executing
production logic. Real-state naming additionally requires a successful, same-SHA
native constant probe and the frozen source-bound legacy timeline adapter.
