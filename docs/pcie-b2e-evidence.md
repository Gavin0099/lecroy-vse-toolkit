# PCIe-B2e：Snapshot Query 驗收

2026-09-30 本地 PASS，未 commit／push／PR／merge。

Packet 225040 的舊 device 查詢有 36 個 named／raw register spans。
LinkControl 的 last write intent 0x42（Packet 10354），last read UNKNOWN。
Command 的 last read 與之後 write 分開，標示 later-write，不當當前硬體值。
Packet 1484414 的新 epoch 未有 config evidence；raw 0x90:2 保持 unnamed／UNKNOWN，
不能把舊裝置 LinkControl map 帶過去。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2e_snapshot_query.py -v`：4 tests PASS。
- Query span／cut、零與未知、partial bytes、later-write、new epoch mapping isolation。
- `artifacts/evidence/pcie-b2e-hang-20260930/verification.json`：兩次 before snapshot
  JSON／Markdown 一致；`before-run1` 為正式 before view，`after` 是新 epoch view。

CLI 可加 `--register 0x90:2` 查 raw offset；不因此聲稱新 device 的 register 意義。
下一 gate 為 B2f observed snapshot diff。

2026-10-02 delivery: 5 focused B2e tests and 86 clean-slice tests PASS. The
snapshot-specific same BDF/VID-DID epoch regression is now in B2e, leaving B2d
independently testable without importing this module. New epoch VID/DID may be
observed while LinkControl name/read/intent remain unknown. Real snapshot JSON
and Markdown replay twice byte-identically to historical before-run1.
