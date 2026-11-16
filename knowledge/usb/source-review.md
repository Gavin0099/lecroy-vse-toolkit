# Primary-source review, 2026-10-21

USB-IF catalogs were inspected through web retrieval. USB2 catalog dated
2025-06-03, USB3.2 Revision1.1 June2022, and PD Revision3.2 Version1.2
(catalog date2026-09-14) are availability references only. Catalog dates do
not establish the revision of a captured device or implement conformance.

USB3.2 Link Layer Test Specification, Revision1.1, March3,2024:
reviewed printed pages27-36 (Polling/LFPS), 37-38 (U0), and41-44
(Recovery subsections). These distinguish state transitions and require
state/ordered-set context. They do not justify inferring an exact state from
an anchor or diagnosing a reset by itself. No timers/assertions are implemented.
Its copyright page grants reproduction for internal use only. No PDF or
verbatim assertion is redistributed here.

Direct HTTP requests to USB-IF returned403; web text was accessible. Thus the
hash for USB-IF entries is this authored review record, NOT original PDF/HTML
bytes. Original-byte pinning remains unavailable. Linux and Microsoft entries
have actual fetched-byte hashes; Linux pins are a fixed commit, not a claim
to be the latest revision. No upstream verification happens at runtime.
