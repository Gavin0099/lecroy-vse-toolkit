# P03：PCIe 原生欄位的本地驗收

這片讓工程師能回查 ACK／NAK sequence、credit 和 TLP 欄位。已完成離線契約、真實 trace
唯讀抽樣、重複執行和 review；接受範圍是 **bounded native fields**，不是完整 P03 資格化。

## 實際證據

| 原生訂閱 | callbacks | 輸出樣本 | 重複結果 |
| --- | ---: | ---: | --- |
| DLLP | 2,147,145 | 73 | 兩次完全相同 |
| TLP | 704 | 51 | 兩次完全相同 |

按原生型別保留前8筆；NAK 實際只有1筆。DLLP 中 ACK754、NAK1；InitFC1 三類各18，
InitFC2 三類各15；UpdateFC_P1,072,784、UpdateFC_NP1,072,775。UpdateFC_Cpl 沒有 callback，
coverage 尚未證明，因此保留 unknown。另732個 DLLP callbacks 不在這次欄位型別白名單中。

TLP 中 MRd32=165、MWr32=203、CfgRd0=32、CfgWr0=29、Msg=2、MsgD=1、Cpl=31、CplD=241。
其餘型別没有樣本，不列為已資格化。

18個型別代表 packet 另走 `ExportToText`；對照 PSN、Length、ACK／NAK sequence、
VC、credit／scale 與 completion ByteCount／LowerAddr 均一致。例如 packet3133 的 ACK sequence
為1405、packet225042 的 NAK sequence 為1682。這是獨立 API 路徑，但共用 LeCroy decoder，
不能當成獨立 protocol compliance oracle。

軟體為 PCIe Suite13.26 Build43，分析用 converted trace SHA-256：
`c6e9646be0624b3efdd2a31796edcfc9e3a517c1429491a8101c7e48f96e15ad`。
各次 readonly copy、來源、script 和 vendor sources 在執行前後一致；未重新轉檔。

## 契約與測試

- [欄位 probe](../tools/pcie_field_probe.py)：每個 event type 只讀適用 members；
  available 保留整數、適用但 API null 保留 unknown、不適用保留 not_applicable。
- [受保護 runner](../tools/run-pcie-field-probe.py)：default preflight，execute 才建立新 readonly copy；
  script／trace hash 不符、結束失敗、source 變動或非 DONE 均拒絕。
- [獨立 fixture 依據](../tests/pcie_fields/fixture-oracles.md)：LC-01 §§5.2.2–3；11項測試涵蓋
  ACK／FC／request／completion、空值、不適用、型別、計數、重複、截斷、namespace 和 source binding。
- [Review](../artifacts/evidence/p03-serial-20261013/p03-review.json)、
  [Manifest](../artifacts/evidence/p03-serial-20261013/manifest.json)、
  [Trace eligibility](../artifacts/evidence/p03-serial-20261013/eligibility.json)。

## 判斷上限

ACK／NAK 的 FCError 回傳 null；不能補成0。Length0 和 scale0 均保持原編碼，沒有補成1024DW
或算出容量。沒有 positive error／非零 scale 樣本，沒有證明所有模式或全部 command types。

Mode、epoch、capture bounds、retention、display filters 仍未知。S01 matrix 的 P03 sampled-ACK
條件也是 partial，原因包括缺 mode；review 接受可重播的原生抽樣輸出，不覆蓋 qualification gate。
P04／P05 還缺適用 replay／credit 規範正文、連續雙向 epoch 與基準；P06 還等 P02 packet membership
和唯一 request 身分。所有既有 PASS 保留原適用範圍。
