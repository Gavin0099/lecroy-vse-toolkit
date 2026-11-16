# P01 PCIe selection checkpoint

依使用者授權，在 U01／U02／U03 的局部 review 通過後，接 PCIe P01。沒有逐片重問；硬體操作、commit／push／merge 及跨 checkout 搬動仍未授權。

工程師現在能区分「這個範圍沒有回傳 TLP／DLLP」與「整份 trace 沒有事件」。指定 converted trace、同一 readonly working copy、六種設定各跑兩次，全部語意輸出一致；每次來源、copy 的 SHA／size／mtime 保持不變，finish=DONE 且 PETracer 退出。

| Selection | Callback count | Index0–200 的 row count | Native level |
| --- | ---: | ---: | ---: |
| packet-all | 3,457,139 | 201 | 0 |
| packet-empty-window（1e9–1e9+1） | 3,457,139 | 0 | 0 |
| packet-tlp | 704 | 0 | 0 |
| packet-dllp | 2,147,145 | 0 | 0 |
| link-all | 703 | 201 | 1 |
| split-all | 225 | 201 | 4 |

TLP／DLLP 都確實存在，卻不在本輪0–200 window；空樣本保持 unknown，不能改成 absent。LINK／SPLIT 的 index 是各自 group namespace，不是 packet number。Native effective range／display filters、capture 起訖／epoch、量測解析度仍未知；沒有 protocol PASS／FAIL 或 complete grouping qualification。

安裝版 named `_SPLIT` 實際為4。LC-01 context表列2，與實測和其他表不一致；本片用 named constant，不猜数字。Time2 保留三個整數元件，未把 ps representation 當量測準確度。

程式：[plan／validator](../tools/pcie_selection_probe.py)、[tests](../tests/selection_pcie/test_pcie_selection_probe.py)。Native execution 使用目前 checkout 已資格化的 `scripts/pcie/com_run_vse.py`，沒有改動它或搬 delivery checkout 的 W1–W5 檔案。Bundled Python 沒有 pywin32，使用已存在的 system Python3.13，不安裝依賴。

[Review evidence](../artifacts/evidence/serial-slices-20261013/p01-review.json) 為 `APPROVE_BOUNDED_SELECTION_TRANSPORT`，只接受指定 SHA／software／profile/window 的對帳。分析 trace 為 `c6e9646b...e15ad`，是先前已授權轉換的13.26格式；沒有再次轉換，也沒有宣稱 index 與原始12.36相同。

P02 的 native levels 可用，但本輪 sources 沒有提供已驗證的 explicit child-packet references；`Metric_NumOfPackets` 不等於 packet list，group index 不替代 packet index。完整 P02 qualification 仍需補足這些 references 與 status／metrics 的適用樣本。P03 的字段增量及 P04–P06 的 replay／credit／completion 規則仍保留獨立的 mode／欄位資格化、規格正文與 fixtures 門檻，不能由 P01 成功自動聲稱已完成。
