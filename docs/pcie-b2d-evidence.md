# PCIe-B2d：Observed state 驗收

2026-10-02 交付驗證：B2d 五項測試保留 state 的同 BDF／VID-DID epoch 隔離。
原 fixture 中額外的 snapshot／mapping 斷言歸入後續 B2e slice，讓 B2d 可在
尚未安裝 B2e 的乾淨主線獨立驗證。這項測試切分不改 production state。

交付 review 另重現 out-of-order Completion 的 last-read 問題：request 10 / completion 40
與 request 20 / completion 30 讀同一 DWORD，cut 40 應保留 completion 40 的值。
共用 B2c read-image helper 改依 Completion packet 更新，新增 B2d 回歸先 FAIL 後 PASS。
這是 last-read 契約的修正；實際 capture 的 B2c mapping 與 B2d state 重播仍與歷史逐位元組一致。

2026-09-30 本地 PASS，未 commit／push／PR／merge。

切換前 state 保存 64 個已讀回 bytes 與 68 個被 write request 選取過的 bytes。
兩者分開，每 byte 有 request／completion packet／access ID；write 不替換 read。
切換後 SDE 的兩種 view 都空，保持 UNKNOWN，不帶入舊裝置值。

最後的 LinkControl write intent（offset 0x90）是 Packet 10354 的 `0x42`。
ASPM mask 0x3 解出 2，即 L1 enable intent；沒有 LinkControl read-back。
與 case 的 Disable ASPM 條件之關係留給 B2g source/scope gate，不在此宣告 FAIL。

## 驗證

- `python -X utf8 -B -m unittest discover -s tests/pcie -p test_b2d_observed_state.py -v`：4 tests PASS。
- 初跑有兩個測試資料問題：共用 read fixture 缺少 write_value=null；真實 0x42
  被錯誤期待為 ASPM 0。補 fixture 欄位、改成獨立確認的 literal value／packet，
  沒有把 production extraction 改成迎合錯誤預期。
- Completion 前不可使用 read、partial BE 不補其他 bytes、zero 可被觀察、
  未觀察 bytes／跨 epoch／BDF／跨 epoch completion 皆保留未知。
- `artifacts/evidence/pcie-b2d-hang-20260930/verification.json` 保存兩次切換前重播
  與切換後 UNKNOWN view 的 hash；目前正式 before-run1，after 為另一 epoch。
