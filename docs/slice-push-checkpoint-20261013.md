# Slice 程式與小型證據交付

使用者於2026-10-13指示「先push上去」，授權建立必要提交並推送目前分支。
目標為 `origin/codex/pcie-d1e-f0-baseline`；沒有 merge／reset／跨 checkout 搬檔。

本次提交 S01、U01／U02／U03、P01／P03、I01／I02、P11／P10 的本地原型、fixtures、
來源登錄、測試與 bounded review 證據。相依 B2 程式取自目前 checkout 的既有 working files，
實際來源與相對 main 的差異見
[dependency audit](../artifacts/evidence/slice-push-20261013/dependency-audit.json)。
有些是先前已交付到 main 的版本，有些是本地 sidecar prototype；這次只出版原驗收版本，沒有整合 main。

## 推送範圍

[Bundle plan](../artifacts/evidence/slice-push-20261013/bundle-plan.json)列出實際路徑、大小、SHA-256
與排除理由。只提交指定程式、schemas、fixtures、文件及小型 JSON／文字／CSV 證據。
Raw `.usb`／`.pex` captures、本機 working copies、大型歷史 timeline JSON、rendered spec page
及其他無關未追蹤成果維持原位置。沒有將大型 capture 改放 LFS 或另外上傳。

## 重播與證據限制

Synthetic contract／field／selection／Recovery／register fixture tests 可在相符 Python／Windows
環境重跑。Native runtime 另需 LeCroy 授權軟體、原 SHA trace 與 COM／VSE，推送不是 runtime 安裝證明。

I01 的 case integration 仍使用 frozen W1–W5 checkout commit `f417eecb`；I02 的 case integration
需要原 C4 saved timeline JSON（單檔約110／156 MB）。這些輸入未包含在交付包，原本的本地
179 Python cases 與10 managed cases 結果仍是當時 scope 的證據，不聲稱一般 fresh clone 可完整重播。
原 provenance／native review 腳本含當時 checkout HEAD／絕對路徑；新的 delivery checks 與歷史驗收分開。

推送不擴大既有 PASS，不將 unknown／抽樣結果改為 compliance 或 root-cause verdict。
Commit、push 與 remote HEAD 證據見
[delivery record](../artifacts/evidence/slice-push-20261013/delivery.json)。
