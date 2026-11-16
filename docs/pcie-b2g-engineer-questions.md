# PCIe-B2g：工程師最低確認清單

**只需要回答：Disable ASPM 要管誰、在哪個階段管、應該是多少，以及看到 write 是否就能判定。Trace 解碼與 packet 證據不用重新確認。**

最少需要回答：

1. 哪個 device／side（並標明 epoch 與 BDF）
2. 哪些 phase
3. ASPM[1:0] expected value
4. Write 是否足以判定，或需要 read-back／等效證據

下方四題與表格是精確填寫版本；請附定義／期待來源。

B1d、B1e、B2a–B2f 在各自已驗證範圍內 COMPLETE。
B2g 目前是 **SOURCE/SCOPE GATE**，不是 FAILED；請補下列四組產品規則。

## 先看這筆事實

Packet **10354**，8.314 sec，Downstream CfgWr0：舊 device `001:00.0`，
observed PCIe capability base 0x80，LinkControl offset 0x90，write DWORD 0x42，
FirstDwBe=0x3／LastDwBe=0；Cpl at 10358，沒有 0x90 read-back。

| Observation name | Write intent | ASPM intent | Effective state | Expected state | Policy result |
| --- | --- | --- | --- | --- | --- |
| L1_ENABLE_WRITE_INTENT | 0x42 | L1（bits=2） | UNKNOWN | UNKNOWN | NOT_EVALUATED |

此前亦有 8658 → Cpl 8660 的 0x42，以及 9915 → Cpl 9918 的 0x40。
三筆 time display 皆為 8.314 sec；不能建立更精細 duration。
RC Root Port LinkControl 未由此 log 取得。Test label 的 scope 未定義，
所以不能判「系統 ASPM 開啟」、「Disable ASPM 違反」或 BSOD root cause。

## 1. Disable ASPM 套在哪一側、哪個 device／epoch 與 BDF？

- [ ] RC Root Port
- [ ] EP
- [ ] 兩側

請按目標裝置／epoch 分列；同一 BDF 在 MUX 前後不能只填一列。

| Side | Device／epoch 身分 | BDF | Applicable phase（對應 Q2） |
| --- | --- | --- | --- |
| RC | ________ | ________ | ________ |
| EP | ________ | ________ | ________ |
| EP | ________ | ________ | ________ |

填寫形式例如 `EP / 7494 controller・pre-switch / 001:00.0 / A`，或
`EP / SDE・post-switch / 001:00.0 / C、D`；這是輸入格式示例，
不表示 trace 已證明裝置名稱與 BDF 的對應。不能確定身分時填 UNKNOWN。
Device／epoch 標籤不等同 identity-continuity proof，不授權跨 epoch 繼承 state。

回答／定義來源：________

## 2. 套在哪些 phase？可複選

- [ ] A. 7494 controller 尚連接時
- [ ] B. MUX disconnect period
- [ ] C. SDE reconnect／training
- [ ] D. SDE L0 之後
- [ ] E. 整個 testcase 都必須維持

各側／device／epoch／BDF 若不同，請分別填：________

## 3. 每個 register／bits 的期待是多少？

請只填需要核對的項目；未知不由工具補定。

| Side | Device／epoch（對應 Q1） | BDF | Phase | Register | Bits | Expected | 定義／期待來源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RC | ________ | ________ | ________ | Link Control | ASPM[1:0] | ________ | ________ |
| EP | ________ | ________ | ________ | Link Control | ASPM[1:0] | ________ | ________ |
| ________ | ________ | ________ | ________ | ________ | ________ | ________ | ________ |

必要的 RC control-order 順序限制（沒有則填無）：________

## 4. 如何驗收：write intent 足夠，還是要 read-back？

- [ ] Write intent 足夠；在指定 scope／phase 看到不符合期待的 write 就算 intent policy violation。
- [ ] 必須有 read-back；沒有讀回只能 INCONCLUSIVE。
- [ ] 可接受等效證據；請定義證據、時點與對應方式：________

各項 register 若採不同依據，請逐項註明：________
Completion acknowledgement 是否只是回覆證據、能否作等效 proof，請明確定義；
工具不自行選擇。回答人／日期／允許工具使用的來源：________

## 保留邊界

- B1d 的 MUX 接通／雙向 L0 與四項不阻擋 v1 的 validation debt 不重開。
- Config state 不跨 device epoch；相同 BDF／offset／VID/DID 不等於 identity continuity proof。
- B2h 仍為 conditional：`0x940h[1]` 需 BDF／BAR 或 config／MMIO 空間、owner、
  bit semantics、write value 與可使用的定義來源。未補 register contract 不搜尋「0x940 write」。
- 要判定 L0 後 SDE 升速／初始化，需更長 capture 或對應資料；不把短尾端未知改成 FAIL。

位元 layout 來源：[Linux v6.12 pci_regs.h](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/uapi/linux/pci_regs.h)。
這只提供欄位解碼，不提供 testcase 的產品期待。
正式 v2 observation：`artifacts/evidence/pcie-b2g-hang-20260930/r1-run1/watchlist-preparation.json`；
分層契約：`docs/pcie-b2g-observation-contract.md`。原 v1 產物保留為歷史。
