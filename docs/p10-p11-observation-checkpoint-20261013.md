# P10／P11：原始設定與 Recovery 狀態點

兩片都完成 bounded checkpoint，接受範圍分別是單一 standard register 的原始位元視圖、
以及具 validity 的已保存 LTSSM 狀態點。尚未完成全部模式／L1SS／EQ／reset 資格化。

## P11 能回答什麼

這份 converted trace 的已保存 window 有22個 LTSSM points。其中9個有效 Recovery points
位於 packet225051、990789、990799、1096915、1096917、1484186、1484200、1484216、1484229；
另有2個 invalid points，保留原始 vector 和來源，不列入 positive state observation。
L0 有2個有效 points；EQ／HotReset 沒有適用樣本，仍 unknown。沒有 PERST#／sideband 證據。

這次在同 SHA trace 上重新執行既有 B1b-0 原生常數 probe，核對 state naming。舊 state source
維持 CORROBORATED_LEGACY 身分，沒有升為新 capture 或完整 state sequence。
原 change-only extractor 沒有比較 validity bit 的改變，可能漏 validity-only transitions；
鄰近 saved points 不能證明連續狀態期間，沒有計算 duration、timeout 或電氣 EQ 結果。

[實作](../tools/pcie_recovery_observations.py)／[獨立 fixtures](../tests/pcie_recovery/fixture-oracles.md)
／[HTML](../artifacts/evidence/p03-serial-20261013/p11-state-points-r3/report.html)
／[JSON](../artifacts/evidence/p03-serial-20261013/p11-state-points-r3/observations.json)
／[Review](../artifacts/evidence/p03-serial-20261013/p11-review.json)。10項測試包括中途開始、invalid／
unknown state、重複／衝突 packet、缺方向、EQ／HotReset、無 PERST 與不推時序。

第一次呼叫曾因 relative OpenFile path 被拒絕。其 owned process／cleanup／hash 證據保留；
殘留 child 最後已退出，absolute-path 重試成功，native process 全部釋放。
失敗沒有算成 probe PASS，也沒有重開或擴大既有 milestone。

## P10 能回答什麼

沿用既有 B2h2 的 CATC merged／write intent／Completion readback 三種證據，只擴 LinkControl
的 CommonClockConfig 與 EnableClockPowerManagement 原始位元，ASPM Control 保留既有語意。
布局來自 [PCI-45 WDK primary layout](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_pci_express_link_control_register)，
頁面更新2026-06-29；本輪重讀 Syntax／selected Members，來源筆記與 SHA 另附。
固定 offset0x90 由既有 Linux v6.12 reference 與 B2c capability evidence 核對，沒有套用到其他裝置。

| Query packet | ASPM | CommonClock | ClockPM | Completion 讀回 |
| --- | ---: | ---: | ---: | --- |
| 3300 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| 10360 | 2 | 1 | 0 | UNKNOWN |

10360 的三欄 CATC merged 與原生 CATC 欄位皆 MATCH；最近 write intent 來自 packet10354，
raw0x42。這不是生效值，也沒有宣稱 clock／CLKREQ# 動作或已進 L1。
RC、device role、查詢位置的 wire state、L1SS named fields、policy 都維持 unknown／未評估。
帶 port-type 限制的 LinkDisable／RetrainLink 沒加入這個 bounded view。

[實作](../tools/pcie_aspm_register_view.py)／[來源化 regdef](pcie-register-defs/linkcontrol-observation.regdef.json)
／[來源筆記](pcie-register-defs/linkcontrol-observation.source.json)
／[Report](../artifacts/evidence/p03-serial-20261013/p10-standard-view-r3/report.md)
／[Review](../artifacts/evidence/p03-serial-20261013/p10-review.json)。6項獨立 fixtures 包括 bit examples、
partial mask、wrong device／epoch／offset、future discovery、source identity／integrity 和 definition drift。

## 相依檔案與保留邊界

P11 的 W1 adapter 在 frozen delivery checkout `f417eecb`，constant parser／probe 在目前 checkout
`c100ee1b`；實際路徑、commit、磁碟 SHA 和 Git blob 分別驗證。P10 沿用 current checkout 的
B2h2／B2d／regdef working files，將實際檔案 SHA 記入輸出；沒有將 untracked code 當成 committed。
兩個 checkout 沒有搬動檔案，沒有 merge／reset／commit／push。

S01 eligibility 保留 partial；現在的 positive observations 不補全 mode／epoch／coverage，也不提供
新的產品政策 PASS。剩餘 candidates 仍按可用輸入與來源逐片放行。
