# W4＋W5：Markdown 與離線 HTML 觀察報告

本 capability 將 W2＋W3 已驗證的時間線轉成可閱讀的報告。兩種格式共用 typed observation
model，引用既有 B1d/B1e 里程碑、config request／Completion、Link/DLLP、segment counts、
GUI samples 與來源 SHA／JSON pointer。HTML 使用原生 details，沒有外部資源或 JavaScript。

## 定稿 invariants 與 local review

| Invariant | 驗證 |
| --- | --- |
| 不盲信衍生 timeline | CLI 重算 source-bound adapter 並比對 canonical bytes；更改 timeline 拒絕 |
| Markdown／HTML 引用同一事實 | 同一 model；12 個既有規則、61 config requests、3 GUI samples、write intent 與 UNKNOWN 狀態 |
| 不增加產品規則 | MUX connectivity、雙向 L0 分開；initial Gen1／target Gen3 仍 INCONCLUSIVE |
| Write 不是 effective state | Packet 10354 為 0x42／L1_ENABLE_WRITE_INTENT；effective/expected UNKNOWN，policy NOT_EVALUATED |
| Read return 保留 Completion anchor | request 不提前宣告讀回；歧義或缺 Completion 不判 timeout |
| 時間／population 不擴張 | 1.312 sec 是 display gap；GUI sample 無 timestamp；segment counts 不加入逐筆 observation 數 |
| 可追溯 | 規則、intent、config、link 與 segment 的來源 pointer 可解析，source bytes 已由 upstream 重驗 |
| 工程師 ground truth 不變成 root cause | device 不可見／BSOD 為回報，crash dump 未驗證 |
| Opaque extension 不變成 report facts | 報告不解讀 extension prose；CLI 仍拒絕非 canonical timeline |
| 離線文字安全 | HTML escaping、Markdown markup escaping、唯一 packet anchors、沒有 remote/script resources |

Local adversarial review 限於上述輸出與證據邊界。任意 JSON parser hardening、產品 ASPM
policy、完整 TS/DLLP extractor、PCIe spec／timer 驗證及 root-cause inference 都不在此範圍。

## 重播與開啟

```text
python -X utf8 -B scripts/pcie/b3d_observation_report.py --timeline artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json --source-root . --output-dir <new-directory>
python -X utf8 -B -m unittest discover -s tests/pcie -p test_b3d*.py -v
```

既有 output directory 會拒絕。Source hyperlinks 使用 output directory 到 repo root 的相對路徑；
移動 HTML/Markdown 必須保留其相對位置與來源檔。JSON pointer 保留在 link text／fragment，
一般 JSON viewer 不一定會自動跳到該 pointer。

兩次 replay 使用相同 directory depth，輸出 hashes 保存於 verification.json；只提交 run1
canonical 報告，第二次輸出留在 ignored runtime。HTML 另以隔離 headless Edge profile 檢查畫面。

## 交付狀態

W1、W2＋W3、W4＋W5 的 bounded waiting-period 工作完成後，下一步回到工程師來源：
`docs/pcie-b2g-engineer-questions.md` 的 Who／When／What／Proof。
這份報告保留 B2g SOURCE_SCOPE_GATE、B2h conditional；沒有完成產品 ASPM evaluation、
B3c／整體 B3d 或 BSOD root cause。四項 validation debt 不阻擋既有 B1d 範圍。
