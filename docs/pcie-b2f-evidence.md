# PCIe-B2f：Observed Snapshot Diff 驗收

2026-09-30 本地 PASS，未 commit／push／PR／merge。
正式產物 `artifacts/evidence/pcie-b2f-hang-20260930/run1/diff.json`／`diff.md`。

真實 MUX before／after 的 36 個 register spans 屬不同 connection epoch，
全部 NOT_COMPARABLE_DEVICE_EPOCH。舊 LinkControl intent 0x42 與新 epoch UNKNOWN
不能說成「ASPM 變 0」或「新 device 初始化失敗」。Read／intent 不互相替代。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2f_snapshot_diff.py -v`：5 tests PASS。
- Fixture 透過新的 read completion／write request 產生同 epoch 變化；缺值與
  不同 epoch／BDF 保持正確界限；CLI 拒絕 snapshot 改值、混 source hash、既有輸出。
- 真實兩次重播 JSON／Markdown 位元組一致，`verification.json` 保存 hash。

下一 gate B2g 需要工程師指定 control-order/watchlist 的 BDF、階段、欄位期待。
目前只有 Q8 case 條件、Q2/Q6 新裝置初始化期待及 Q1 未定義的 0x940h[1]，
不能自行把 register bits 的解碼當成已經獲得完整產品 watchlist。

## 2026-10-02 current delivery

Six focused tests and 93 clean-slice tests PASS. Two current diff JSON/Markdown
replays are byte-identical under `artifacts/evidence/pcie-b2f-delivery-20261002`.
Inputs use the corrected one-byte CapabilityPointer snapshot from B2e delivery
and a fresh after-reconnect raw 0x90:2 query. That raw query has no inherited
LinkControl name or value for SDE. All cross-epoch rows remain not comparable.
The earlier pointer-width snapshot fails current source recomputation, before
output is created. Historical 2026-09-30 diffs remain earlier-revision evidence.
