# B1c 離線整理器依賴交付

2026-10-02：主線原先沒有 PCIe scripts；本 PR 只交付 B1d 需要的 B1c 離線能力。
既有 checkpoint branch 的 GUI 操作、extractor、triage、治理維護不在此 PR。

## 契約

- 讀取已命名的 B1b segment / records；PASS summary 必須綁定 timeline SHA-256。
- 保留逐筆 link / LTSSM records 與區間 counters 的差別，interval threshold 是顯示參數。
- 使用 x2 範圍資料時，phase HasErrors 與範圍總數核對；GUI error label 只代表抽樣。
- Carried state 不能代替新觀察；LTSSM valid flag、未知 subtype 與方向限制保留。
- 輸出拒絕既存目錄；沒有產品判定、MUX 接通推論或根因。

來源為既有 B1b named export、B1c-x2 衍生計數、owner 已接受的 GUI observation record。
原始 capture 與 vendor samples 未納入；歷史 JSON 的外部截圖／路徑是 provenance，
本 PR 不宣稱重新操作 GUI 或重新核對截圖。B1b 與 x2 extractor 也未在此交付。

## 驗證

```powershell
python -X utf8 -B -m unittest discover -s tests/pcie -p test_b1c_training_timeline.py -v
python -X utf8 -B scripts/pcie/b1c_training_timeline.py --timeline artifacts/evidence/pcie-b1b-hang-20260914/window-export/export/timeline.json --summary artifacts/evidence/pcie-b1b-hang-20260914/window-export/export/summary.json --x2-haserrors artifacts/evidence/pcie-b1c-x2-hang-20260915/export/haserrors.json --x2-summary artifacts/evidence/pcie-b1c-x2-hang-20260915/export/summary.json --gui-observations artifacts/evidence/pcie-b1c-x1x3-hang-20260915/gui-observations.json --output-dir <new-output-directory>
```

在乾淨交付 checkout 執行 focused tests，真實輸入重播兩次並與既有 r1 training.json
逐位元組比對。這證明 offline replay，沒有新的 runtime／完整 PCIe 規範驗證。
