# PCIe／USB 來源地圖（2026-10-13）

這份地圖把下一輪 probe 與規則研究所需的來源分開登錄。共 **102 筆來源紀錄**（PCI 53、USB 25、LeCroy 本機 16、OS 8），另有 **66 筆 USB bundle 成員清單**。同頁重複紀錄、bundle 與其子文件均保留，所以這些數字不代表 168 份獨立文件，也不代表已讀全文。

精確欄位、版本、存取觀察、SHA-256、API／field 與 bundle 清單見 [JSON 登錄](pcie-usb-source-register-20261013.json)。研究結果的實作順序、依賴與驗收另見 [slice 計畫](pcie-usb-spec-slices-20261013.md)。本文件沒有執行 analyzer、COM、硬體、debugger 或 compliance 工具；本機文件和範例是來源證據，不能增加 runtime PASS 的範圍。

## 範圍與閱讀層級

| 家族 | 已覆蓋的入口與閱讀 | 本輪適用邊界 |
| --- | --- | --- |
| PCIe non-Flit Gen1–5 | Base 1.1–5.0、對應 errata、Config／LLTL／PHY test catalog；AER／DPC、ASPM／L1SS／LTR、reset／hotplug 相關 ECN 公開說明 | 多數規範本文仍有存取門檻；公開摘要不能補齊數值時限、完整 credit／completion／replay 規則。 |
| PCIe 新版本與平台 | Base 6.5／7.1、6.x tests、CEM／Firmware／Code & ID／M.2 相關入口 | 保留版本與 form factor 前提；Flit 規則不直接套到現有 non-Flit trace。 |
| USB3／SuperSpeed | USB 3.2 Rev1.1、Link Test Rev1.1 的指定章節；CV、Hub LVS／CV、xHCI interop 與 electrical catalogs | 先驗證速率／lane／port role、capture coverage 與 analyzer mapping，再選適用條款。 |
| USB2 LS／FS／HS | Rev2.0 base 的 reset／suspend／resume／enumeration 章節；ECN／errata／CV／electrical 入口 | USB2 是有條件分支，不作為 `_USB3_*` 事件的直接規則來源。 |
| LeCroy 安裝來源 | PCIe 13.26、USB 10.40 安裝文件、constants、helpers 與範例；各檔 SHA 保留 | 文件可指出候選欄位與預設選取；來源已讀不等於該 runtime／trace 已通過。 |
| OS／平台錯誤資料 | WHEA／CPER／WinDbg 文件、Linux AER／error recovery、USB ETW／usbmon | OS 記錄、HCD request 與線上封包是不同觀測面；需 ValidBits、關聯與時間依據。 |
| 相鄰 USB 家族 | USB4、Type-C、PD、Intel xHCI、BOT／UAS 官方入口 | metadata 為主；只有產品問題與對應事件／descriptor／controller evidence 出現才納入實作。 |

`metadata_only` 表示只讀 metadata、公開摘要、封面、目錄或 scope，不表示已讀規範正文；`catalog_reviewed` 表示目錄／program／存取頁已讀；`sections_reviewed` 只涵蓋登錄的章節或 source lines。取得或解析 PDF、解開 ZIP 都不會提高閱讀深度。下表「本文已取得」只描述存取狀態，閱讀欄才描述實際讀到哪裡。沒有任何一列宣稱整份全文已讀。

## 版本與取得門檻

- USB2 bundle 的 **2025-06-03** 是 package／catalog 日期，base 仍是 **Revision 2.0、2000-04-27**。USB3.2 base **Rev1.1（2022）**、Link Test **Rev1.1（2024）**、CV **Rev1.22（2019）** 各有自己的版本軸；同一 revision 數字不表示同時發布。見 USB-01、03、05、08。
- USB3.2 overview 的 interop rev1.03 與 library／PDF 不同；本次採實際核對的 **Rev1.04（June 2025）**。ECN bundle 內多份標註適用 Rev1.0，必須逐條確認是否已併入 Rev1.1，不能全部再加一次 override。見 USB-02、12。
- PCI-35 Code & ID 有會員入口，也有 **PCI-36 非會員 agreement route**；後者要提供資料、同意條款及完成提交，本輪未操作。其他會員全文也沒有繞過登入或付費；只有 `login_redirect_verified` 欄位明載的來源實際核對過登入轉址，不能說每份都已試下載。
- PCI-51 僅核對公開 wrapper，本文未讀；**LC-02 安裝版 Automation Manual 的指定正文已讀**。兩者不能合併成「Automation Manual 沒有讀」。PCI-53 公開 PDF 只讀封面／目錄，標為 `metadata_only`；LC-03 是另一個安裝檔與閱讀紀錄。
- 公開 PCIe VSE manual **13.40**（PCI-37）與本機 **13.26**（LC-01）需分開。USB VSE manual **v9.12／Suite v10.13+**（LC-04）和安裝的 **10.40 build6309** 也不能視為全部 field 已驗證。
- 本機 audit 的 runtime 與兩個 checkout 版本保留在 JSON。這是當時的唯讀 snapshot，不是文件新增後的工作樹狀態，也不能把兩個 checkout 的能力誤算成同一棵已驗證版本。

## 已能改變切片順序的來源

| 問題 | 已讀來源與定位 | 對後續切片的直接影響 |
| --- | --- | --- |
| 匯出是否漏掉失敗／未完成事件 | LC-04，SendTransfer PDF168、SendPktsWithBadCRC PDF170；LC-02 ExportToText PDF366–367 | USB `SendTransfer` 預設 `completed=1`，bad CRC 封包預設不送；PCIe 文字匯出還受 display-hidden packets 影響。先做 selection／coverage probe，才解釋「沒看到」。 |
| 是否需要從零重建 transfer | LC-04 §5.2.2、§5.2.4；LC-09–11 原生 helper／範例；LC-01 §5.2.10–.11 | 先驗證原生 transaction／transfer／link／split 的輸出與 grouping，保留完整／不完整範圍；再決定哪些欄位需 adapter 或補充重建。 |
| USB LINK_CMD、LFPS、LTSSM 語義能否取到 | LC-04 PDF30–32、171–174；LC-08–09、12；USB-01 §6.9、USB-05 選定 TD | `LnkCmd`、`LinkCmdInfo`、CRC5 與 `_2` 等有來源候選；LTSSM 專用 state member 尚未確認。generic field lookup 必須使用實際 GUI label，raw enum 不可按規範數字猜對應。 |
| 能否把 NRDY 後缺 ERDY 判違規 | USB-01 §8.10.1–.3 | 規範容許 host 在尚未收到 ERDY 時恢復交易；單靠「NRDY→沒有 ERDY」不能判錯。需 endpoint、direction、flow-control context 與 capture coverage。 |
| PCIe 第一個 UpdateFC 能否作 initial credit | PCI-38 §11.7；PCI-40 Flow Control Credit Information | 沒有 InitFC 或其他可靠初始值時，不能推出絕對餘額；IP interface 描述也不能當 wire encoding oracle。 |
| OS 錯誤能否與 CATC 直接合一 | OS-02、04、06–08；PCI-41–45 | 先保留 ValidBits、來源時鐘、Activity ID／request identity；0x124、AER log、ETW 或 usbmon 都不能單獨證明同一線上事件或根因。 |

這些是選取、欄位與規則前提的新資訊，不會自行撤銷既有範圍內的 PASS。新 slice 仍要把 probe、adapter 與 evaluator 的證據分開。

## 來源逐筆索引

日期保持原來源的分辨方式；`catalog`、`cover`、`history`、PDF metadata 和查核日期不是同一件事。沒有確認 document date 的來源保留未確認，不以查核日補成版本日期。完整限制和 API／field 名單都在 JSON。


### PCIe 與第一手補充（53）

| ID | 來源／版本／日期 | 取得與閱讀 | 已讀定位及適用限制 |
| --- | --- | --- | --- |
| PCI-01 | [PCI-SIG Specifications Library](<https://pcisig.com/specifications?PageSpeed=noscript&speclib=code>)<br>live catalog<br>checked 2026-10-13 | 公開目錄／頁面<br>目錄／入口已讀 | Base, ECN, Errata, Test, Firmware, Code & ID<br>索引列出不等於已取得全文；新版本不等於適用現有 trace |
| PCI-02 | [PCI Express Base Specification](<https://pcisig.com/PCIExpress/Specs/Base/_1.1>)<br>1.1<br>2005-03-08 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>未取得條文；不可由摘要形成 Gen1 normative verdict |
| PCI-03 | [PCI Express Base Specification](<https://pcisig.com/PCIExpress/Specs/Base/_2.1>)<br>2.1<br>2009-03-04 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>未取得條文；不可由摘要形成 Gen2 normative verdict |
| PCI-04 | [PCI Express Base Specification](<https://pcisig.com/PCIExpress/Specs/Base/_3.1a>)<br>3.1a<br>2015-12-07 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>未取得條文；Gen3 capability/ECN applicability 要另確認 |
| PCI-05 | [PCI Express Base Specification](<https://pcisig.com/PCIExpress/Specs/Base/_4.0_1.0>)<br>4.0 v1.0<br>2017-10-05 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>未取得條文；不能當數值時限 oracle |
| PCI-06 | [PCI Express Base Specification](<https://pcisig.com/PCIExpress/Specs/Base/_5.0_1.0>)<br>5.0 v1.0<br>2019-05-28 | 公開摘要；會員全文未取得<br>僅 metadata | metadata and related ECN list<br>non-Flit 規範候選；全文未讀不得聲稱全 Base 審查 |
| PCI-07 | [Errata for Base 3.1 / SR-IOV 1.1 / ATS 1.1 / M.2 1.0](<https://pcisig.com/PCIExpress/Errata/Base/_3.1_SingleRootIOVirtualizationandSharing_1.1_AddressTranslationandSharing_1.1_andM.2_1.0>)<br>final against Base3.1a<br>2018-01-05 | 公開摘要；會員全文未取得<br>僅 metadata | release note only<br>不能由發行摘要知道全部修正條文 |
| PCI-08 | [PCI Express Base Specification Errata](<https://pcisig.com/PCIExpress/Errata/Base/_4.0>)<br>4.0 final<br>2019-09-02 | 公開摘要；會員全文未取得<br>僅 metadata | release note only<br>未逐條比對 errata |
| PCI-09 | [PCI Express Base Specification Errata](<https://pcisig.com/PCIExpress/Errata/Base/_5.0>)<br>5.0<br>2022-01-07 | 公開摘要；會員全文未取得<br>僅 metadata | release note: corresponds to errata included in Base6.0 v0.9/v1.0<br>Base6 收錄舊版 errata 不代表 Flit 條文適用舊 trace |
| PCI-10 | [PCI Express Base Specification](<https://pcisig.com/specification/pci-express-base-specification-revision-65>)<br>6.5<br>2026-09-17 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>現行目錄邊界；不納入 non-Flit Gen1-5 規則實作 |
| PCI-11 | [PCI Express Base Specification](<https://pcisig.com/specification/pci-express-base-specification-revision-71>)<br>7.1<br>2026-09-17 | 公開摘要；會員全文未取得<br>僅 metadata | metadata only<br>現行目錄邊界；不納入 non-Flit Gen1-5 規則實作 |
| PCI-12 | [PCI Express Architecture Configuration Space Test Specification](<https://pcisig.com/PCIExpress/Specs/Test/ArchitectureConfigurationSpaceTest_5.0_1.0>)<br>5.0 v1.0<br>2022-04-14 | 公開摘要；會員全文未取得<br>僅 metadata | scope summary<br>被動 configuration snapshot 不是 PCIECV conformance test |
| PCI-13 | [PCI Express Architecture Link Layer and Transaction Layer Test Specification](<https://pcisig.com/PCIExpress/Specs/Test/ArchitectureLinkLayerandTransactionLayerTest_5.0_1.0>)<br>5.0 v1.0<br>2022-04-14 | 公開摘要；會員全文未取得<br>僅 metadata | scope summary<br>未取得 test algorithm/MOI；離線觀測不能稱 compliance |
| PCI-14 | [PCI Express Architecture PHY Test Specification](<https://pcisig.com/PCIExpress/Spec/Test/ArchitecturePHYTest_5.1>)<br>5.1<br>2024-05-03 | 公開摘要；會員全文未取得<br>僅 metadata | scope and companion-document list<br>電氣測試需實體量測；trace 不證明 eye/jitter/BER 合規 |
| PCI-15 | [PCI Express Architecture Configuration Space Test Specification](<https://pcisig.com/specification/pci-express-architecture-configuration-space-test-specification-revision-6x>)<br>6.x<br>2026-07-22 | 公開摘要；會員全文未取得<br>僅 metadata | scope and test fails/warns description<br>current index only；不能跨版本套 fail/warn |
| PCI-16 | [PCI Express Architecture Link Layer and Transaction Layer Test Specification](<https://pcisig.com/specification/pci-express-architecture-link-layer-and-transaction-layer-test-specification-revision>)<br>6.x<br>2026-07-22 | 公開摘要；會員全文未取得<br>僅 metadata | scope and stated exclusions<br>摘要明說非所有 LL/TL requirements 的完整 test set；不測 retimer 本體 |
| PCI-17 | [PCI Express Architecture PHY Test Specification](<https://pcisig.com/specification/pci-express-architecture-phy-test-specification-revision-6x>)<br>6.x<br>2026-06-24 | 公開摘要；會員全文未取得<br>僅 metadata | scope and companion-document list<br>current index only；不得據此做舊 trace PHY verdict |
| PCI-18 | [PCIe 5.0 Protocol and Electrical Compliance Testing Deep Dive](<https://pcisig.com/sites/default/files/files/PCI-SIG%20PCIe%205.0%20Compliance%20Webinar_1.25.23_FINAL.pdf>)<br>official webinar PDF<br>URL dated 2023-01-25 | 公開本文已取得<br>指定段落已讀 | slides13-20,25-29<br>教學簡報不是 normative algorithm；後續 ECN 可改變 test status |
| PCI-19 | [Change Link and Transaction test case 54-20 to informative](<https://pcisig.com/PCI%20Express/ECN/Test/ChangeLinkandTransactiontestcase54-20toinformative>)<br>LL/TL5.0 v1.0 ECN<br>2023-05-23 | 公開摘要；會員全文未取得<br>僅 metadata | public explanation<br>Bad ECRC54-20 為 informative；不能照較早 list 一律稱 mandatory |
| PCI-20 | [Downstream Port Containment (DPC)](<https://pcisig.com/PCIExpress/ECN/Base/DownstreamPortContainment>)<br>Base3.0 ECN<br>2012-02-09 | 公開摘要；會員全文未取得<br>僅 metadata | public mechanism summary<br>link down 不能單憑時序判 DPC；先證明 capability/status |
| PCI-21 | [Enhanced DPC (eDPC)](<https://pcisig.com/PCIExpress/ECN/Base/EnhancedDPC>)<br>Base3.0+DPC ECN<br>2012-11-15 | 公開摘要；會員全文未取得<br>僅 metadata | public RP extensions summary<br>含 RP PIO control、Completion synthesis、software-trigger DPC；不能假定產品具備 |
| PCI-22 | [Downstream Port Containment Related Enhancements](<https://pcisig.com/PCIFirmware/ECN/Firmware/DownstreamPortContainmentRelatedEnhancements>)<br>Firmware3.2 ECN<br>2019-02-14 | 公開摘要；會員全文未取得<br>僅 metadata | affected sections4.5.1,4.5.2.4,4.6.12,4.6.13<br>OS/FW ownership 需要平台證據；wire trace 不足 |
| PCI-23 | [Internal Error Reporting](<https://pcisig.com/PCIExpress/ECN/Base/InternalErrorReporting>)<br>Base2.0 ECN<br>2008-04-24 | 公開摘要；會員全文未取得<br>僅 metadata | public scope and multiple error header summary<br>PCIe相關 internal error 不代表所有 vendor component errors 可由 AER 解釋 |
| PCI-24 | [L1 PM Substates with CLKREQ](<https://pcisig.com/PCIExpress/ECN/Base/L1PMSubstateswithCLKREQ_1.0a>)<br>rev1.0a ECN<br>2013-05-30 | 公開摘要；會員全文未取得<br>僅 metadata | public scope: ASPM/PCI-PM L1 and per-link CLKREQ<br>LTSSM L1 不能單獨分辨實際 L1.1/L1.2 或功耗 |
| PCI-25 | [ASPM Optionality](<https://pcisig.com/PCIExpress/ECN/Base/ASPMOptionality>)<br>Base2.1 ECN<br>2009-08-20 | 公開摘要；會員全文未取得<br>僅 metadata | public support/enable/entry distinctions<br>啟用 L0s 不等於必須觀察到 entry；form factor可能另有要求 |
| PCI-26 | [Latency Tolerance Reporting](<https://pcisig.com/PCIExpress/ECN/Base/LatencyToleranceReporting>)<br>Base2.0 ECN<br>2008-08-14 | 公開摘要；會員全文未取得<br>僅 metadata | public service-latency mechanism summary<br>未讀 exact field encoding/aggregation/rate rules；不自行設 latency threshold |
| PCI-27 | [LTR OS Guidance](<https://pcisig.com/PCIExpress/ECN/Firmware/LTROSGuidance>)<br>Firmware3.3 ECN<br>2025-11-13 | 公開摘要；會員全文未取得<br>僅 metadata | public hierarchy configuration summary<br>未讀正文；平台採用與適用性未知 |
| PCI-28 | [LTR Enhancements for MFD](<https://pcisig.com/PCIExpress/ECN/Base/LTREnhancementsforMFD>)<br>Base6.3 ECN<br>2025-06-11 | 公開摘要；會員全文未取得<br>僅 metadata | public capability/FLR summary<br>新 capability 不可套於舊 trace/device；僅版本排除清單 |
| PCI-29 | [PCIe Link Activation](<https://pcisig.com/PCIExpress/ECN/Base/PCIeLinkActivation>)<br>Base4.0 ECN<br>2017-12-07 | 公開摘要；會員全文未取得<br>僅 metadata | public software-initiated L1SS exit summary<br>避免 PM stall 的機制存在不等於觀測產品採用 |
| PCI-30 | [Relaxed Detect Timing](<https://pcisig.com/PCI%20Express/ECN/Base/RelaxedDetectTiming>)<br>Base5.0 ECN<br>2021-12-08 | 公開摘要；會員全文未取得<br>僅 metadata | public exact applicability statement<br>20ms至100ms只針對支援>5GT/s元件的Fundamental Reset結束至Detect；不可當泛用training timeout |
| PCI-31 | [Readiness Notifications (RN)](<https://pcisig.com/PCIExpress/ECN/Base/ReadinessNotifications>)<br>Base3.0 and companion specs ECN<br>2013-08-29 | 公開摘要；會員全文未取得<br>僅 metadata | public post-power/reset/PM configuration-readiness summary<br>看不到 Configuration Request 不能直接判初始化失敗；RN capability與完整時間窗未知 |
| PCI-32 | [Async Hot-Plug Updates](<https://pcisig.com/PCIExpress/ECN/Base/AsyncHot-PlugUpdates>)<br>Base4.0 ECN<br>2018-12-12 | 公開摘要；會員全文未取得<br>僅 metadata | public bullets1-5<br>ERR_COR可能有firmware-signaling subclass；不能把每個ERR_COR都當普通correctable link error |
| PCI-33 | [Power-up requirements for PCIe side bands (PERST#, etc.)](<https://pcisig.com/PCIExpress/ECN/M.2/Power-uprequirementsforPCIesidebandsPERST_etc.>)<br>M.2 v1.0 ECN<br>2014-09-18 | 公開摘要；會員全文未取得<br>僅 metadata | public changes to former3.1.3.2.1<br>M.2 reset timing有implementation-specific/recommended區別；不可跨form factor搬門檻 |
| PCI-34 | [_HPX and PCIe Completion Timeout related _OSC Enhancements](<https://pcisig.com/PCIFirmware/ECN/Firmware/_HPXandPCIeCompletionTimeoutrelated_OSCEnhancements>)<br>Firmware3.2 ECN<br>2019-03-17 | 公開摘要；會員全文未取得<br>僅 metadata | public affected4.5.1,4.5.2.4<br>Completion Timeout control ownership不能從TLP或短capture推斷 |
| PCI-35 | [PCI Code and ID Assignment Specification](<https://pcisig.com/PCIExpress/Spec/Base/CodeandIDAssignment_1.19>)<br>1.19<br>2025-06-11 | 會員／非會員條款兩路；全文未取<br>僅 metadata | public Class/Capability/Extended Capability ID scope<br>尚未取得ID表全文；未讀header不可命名capability |
| PCI-36 | [PCI Code and ID Assignment Specification Agreement](<https://pcisig.com/pci-code-and-id-assignment-specification-agreement>)<br>live access gate<br>checked2026-10-13 | 條款／提交門檻，未完成<br>目錄／入口已讀 | access form only<br>不能將non-member free記為無條件已取得；需使用者自行提供合法可用文件或具體授權 |
| PCI-37 | [PCIe Protocol Analysis Verification Script Engine Reference Manual](<https://cdn.teledynelecroy.com/files/manuals/petracer_vse_manual.pdf>)<br>13.40<br>2026-09-03 | 公開本文已取得<br>指定段落已讀 | 5.2.1-5.3,5.8-5.12,8.1-8.3; cover<br>documented fields不證明安裝版可用；numeric event levels在不同表不一致，須用安裝版constants及fixture核對 |
| PCI-38 | [PETracer Summit and Summit T2-16 User Manual](<https://cdn.teledynelecroy.com/files/manuals/pcie_summit_user_manual.pdf>)<br>software7.30<br>2015-02-02 | 公開本文已取得<br>指定段落已讀 | 11.7 printed191<br>舊工具版本；未捕捉InitFC需initial-credit evidence，不能從第一個UpdateFC推定絕對餘額 |
| PCI-39 | [Versal CPM PCIe Product Guide: Completer Completion Descriptor Format](<https://docs.amd.com/r/3.3-English/pg346-cpm-pcie/Completer-Completion-Descriptor-Format?contentId=pEh4XcohN3uFqiFePvYL_A>)<br>PG346 v3.3<br>2023-05-16 | 公開本文已取得<br>指定段落已讀 | Completer Completion Descriptor Fields<br>AXI descriptor不是wire TLP layout；可支持coverage設計但不能替代適用Base規範 |
| PCI-40 | [7 Series PCIe Product Guide: Flow Control Credit Information](<https://docs.amd.com/r/en-US/pg054-7series-pcie/Flow-Control-Credit-Information>)<br>PG054 v3.3<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Flow Control Information Types; six credit pools<br>IP interface values與wire encoding/實際平台不同；不可直接套用credit oracle |
| PCI-41 | [Linux PCI Express AER Driver Guide](<https://docs.kernel.org/PCI/pcieaer-howto.html>)<br>live kernel docs<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | 8.1.2,8.2.2-8.2.5,8.3<br>Linux ownership/logging不是Windows行為；未記錄不等於無錯誤 同頁另一筆：OS-08。 |
| PCI-42 | [Linux PCI Error Recovery](<https://docs.kernel.org/PCI/pci-error-recovery.html>)<br>live kernel docs<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | 7.1 error event, link reset, slot reset, resume<br>platform/driver callback policy不等於wire invariant |
| PCI-43 | [WHEA_PCIEXPRESS_ERROR_SECTION](<https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_whea_pciexpress_error_section>)<br>WDK reference<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Syntax, ValidBits, ExpressCapability, AerInfo<br>無效欄位必須保留unknown；WHEA記錄不直接證明BSOD根因 同頁另一筆：OS-02。 |
| PCI-44 | [PCI_EXPRESS_AER_CAPABILITY](<https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/miniport/ns-miniport-_pci_express_aer_capability>)<br>WDK miniport.h reference<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | status/mask/severity/header log; port-type variants<br>SDK型別不是所有裝置統一layout；文字有疑似copy錯誤，需對SDK及適用spec |
| PCI-45 | [PCI_EXPRESS_LINK_CONTROL_REGISTER](<https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_pci_express_link_control_register>)<br>WDK ntddk.h reference<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | ActiveStatePMControl, RetrainLink, LinkDisable, Clock PM<br>值解碼不等於硬體生效，更不等於產品政策 |
| PCI-46 | [Teledyne LeCroy PCI Express Product Manuals](<https://www.teledynelecroy.com/protocolanalyzer/pci-express/resources/product-manuals>)<br>live catalog<br>checked2026-10-13 | 公開目錄／頁面<br>目錄／入口已讀 | VSE, Automation, file-based decoder, Gen5 analyzer<br>列出連結不代表安裝版或所有內容已核驗 |
| PCI-47 | [PCI Express Architecture Platform Init/Config](<https://pcisig.com/PCIExpress/Specs/Base/ArchitecturePlatformInitConfig_3.0>)<br>3.0<br>2013-06-18 | 公開摘要；會員全文未取得<br>僅 metadata | public scope summary<br>historical firmware test scope；不是最新compliance全套 |
| PCI-48 | [PCI-SIG Authorized Test Lab Program](<https://pcisig.com/developers/authorized-test-lab-program>)<br>live program<br>checked2026-10-13 | 公開目錄／頁面<br>目錄／入口已讀 | Gen4/5 up to32GT/s; approved MOI/equipment<br>offline checker PASS不等於實驗室compliance/Integrators List |
| PCI-49 | [PCI Express Card Electromechanical Specification](<https://pcisig.com/PCIExpress/Specs/CEM/CardElectromechanical_5.0>)<br>5.0<br>2021-06-18 | 公開摘要；會員全文未取得<br>僅 metadata | public scope summary<br>form factor與sideband/electrical要求不能只靠Base或protocol trace |
| PCI-50 | [PCI Firmware Specification](<https://pcisig.com/PCIConventional/Specs/Firmware/_3.3>)<br>3.3<br>2021-02-11 | 公開摘要；會員全文未取得<br>僅 metadata | public scope summary<br>FW/OS ownership與policy全文尚未取得 |
| PCI-51 | [PCIe Automation API Manual](<https://www.teledynelecroy.com/doc/docview.aspx?id=13898>)<br>not yet extracted<br>文件日期未另確認 | 官方入口；本文未讀<br>僅 metadata | not reviewed<br>未讀API本文；不得據此新增COM呼叫 |
| PCI-52 | [PCIe Gen5 Protocol Analyzer User Manual](<https://cdn.teledynelecroy.com/files/manuals/pciegen5_protocolanalyzer_usermanual.pdf>)<br>not extracted<br>文件日期未另確認 | 官方入口；本文未讀<br>僅 metadata | not reviewed<br>只有定位文件，不能宣稱正文已讀或功能在安裝版可用 |
| PCI-53 | [File-Based Decoding Manual](<https://cdn.teledynelecroy.com/files/manuals/petracer-file-based-decoding-manual.pdf>)<br>PCI Express Protocol Analysis 11.37<br>generated 2020-03-10 09:11 | 公開 PDF 已取得<br>僅 metadata | Cover and table of contents only<br>沒有讀decoder本文；不據此重啟.pecfgdec路徑、不推定native API或目前13.26支援 |


### USB 官方與 class／host 相關來源（25）

| ID | 來源／版本／日期 | 取得與閱讀 | 已讀定位及適用限制 |
| --- | --- | --- | --- |
| USB-01 | [USB 3.2 base specification](<https://www.usb.org/document-library/usb-32-revision-11-june-2022>)<br>Revision 1.1<br>June 2022; catalog 2022-06-03 | 公開 bundle 已下載<br>指定段落已讀 | §6.9.1–.2；§7.2.4.1.2–.3；§7.5 selected cross-reference；§8.5.2–.3、8.10.1–.3；§9.1.2、9.4.6–.7、9.6.7<br>Current SuperSpeed/Enhanced SuperSpeed research; actual operating mode and analyzer field mapping still required |
| USB-02 | [USB 3.2 bundled ECNs and Appendix E redline](<https://www.usb.org/document-library/usb-32-revision-11-june-2022>)<br>Per-file; not normalized<br>Bundle June 2022; individual dates not fully verified | 公開 bundle 已下載<br>僅 metadata | 未讀本文；Retimer/polling, training symbols, LFPS, CRC, PHY scope screening<br>Retimer/polling, training symbols, LFPS, CRC, PHY scope screening |
| USB-03 | [USB 2.0 base specification](<https://www.usb.org/document-library/usb-20-specification>)<br>Revision 2.0<br>2000-04-27; catalog/bundle 2025-06-03 | 公開 bundle 已下載<br>指定段落已讀 | 7.1.7.5 Reset；7.1.7.6 Suspend；7.1.7.7 Resume；9.1.2 Enumeration<br>Conditional USB2 LS/FS/HS branch only; not a rule source for current _USB3_* events |
| USB-04 | [USB 2.0 bundle ECNs, errata and supplements](<https://www.usb.org/document-library/usb-20-specification>)<br>Per-file; not normalized<br>Catalog/bundle 2025-06-03 | 公開 bundle 已下載<br>僅 metadata | 未讀本文；USB2 LPM, reset/connect, SOF, descriptors; electrical supplements only with electrical evidence<br>USB2 LPM, reset/connect, SOF, descriptors; electrical supplements only with electrical evidence |
| USB-05 | [USB 3.2 Link Layer Test Specification](<https://usb.org/document-library/usb-32-link-layer-test-specification>)<br>Revision 1.1<br>2024-03-03; catalog 2024-03-04 | 公開 PDF 已取得<br>指定段落已讀 | TD6.5；TD7.1；TD7.13-.17；TD7.23-.29；selected assertions for 7.5 / power states<br>SuperSpeed/SSP link sequences; test-port role, Gen/lane mode, retimer applicability |
| USB-06 | [SuperSpeed Hub LVS Test Specification](<https://www.usb.org/document-library/usb-3-hub-lvs-test-specification>)<br>Revision 1.15<br>2019-11-21; catalog 2020-06-02 | 公開 PDF 已取得<br>僅 metadata | Scope/contents only: TD10.101-.130<br>Hubs and compound devices with exposed downstream ports |
| USB-07 | [USB3CV and XHCICV CTS package](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Package August 2025<br>Catalog 2025-08-06 | 公開 bundle 已下載<br>僅 metadata | 未讀本文；Document source bundle only<br>Document source bundle only |
| USB-08 | [USB Command Verifier CTS for USB 3.2 Architecture](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Revision 1.22<br>Cover 2019-07-10; history entry 2019-02-28 | 公開 bundle 已下載<br>指定段落已讀 | TD9.6 Endpoint Companion；TD9.7 BOS (opening test steps)；TD9.23 Reset Device；TD9.24 U1/U2 (selected steps)<br>Descriptor/EP0 and power-feature observation candidates |
| USB-09 | [USB 3.2 Hub Compliance Test Specification](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Revision 1.21<br>Cover 2019-07-10; history 2019-02-07 | 公開 bundle 已下載<br>僅 metadata | Contents only: TD10.1-.25 etc.<br>Conditional hub descriptor, port-feature/status/change-bit support |
| USB-10 | [USB Command Verifier CTS for USB 2.0](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Revision 1.42<br>Cover 2019-06-19; running header 2019-07-10 | 公開 bundle 已下載<br>僅 metadata | Introduction only: Chapters 9 / 11 scope<br>Conditional USB2 descriptors/standard commands/hubs |
| USB-11 | [xHCI Compliance Test Specification](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Revision 1.20<br>Cover August 2025; history change 2025-01-09 | 公開 bundle 已下載<br>僅 metadata | Scope/revision history only<br>Conditional host-controller register/ring evidence |
| USB-12 | [xHCI Interoperability Test Procedures for Peripherals, Hubs and Hosts](<https://www.usb.org/document-library/xhci-interoperability-test-procedures-peripherals-hubs-and-hosts>)<br>Revision 1.04<br>June 2025; catalog 2025-06-03 | 公開 PDF 已取得<br>指定段落已讀 | Cover/revision history；1.1 Equipment；1.2 Software；1.3 logistical overview<br>Scenario coverage: topology, reconnect, power states, device operation |
| USB-13 | [USB 3.2 Electrical Compliance Test Specification](<https://www.usb.org/document-library/usb-32-electrical-compliance-test-specification>)<br>Revision 1.8<br>Catalog 2026-07-28; overview says 2026-06-30 | 公開 PDF 已取得<br>僅 metadata | Cover/metadata only<br>Electrical boundary catalog; scope/BERT/fixtures required |
| USB-14 | [USB 2.0 Electrical Compliance Test Specification](<https://www.usb.org/document-library/usb-20-electrical-compliance-test-specification>)<br>Version 1.08<br>Cover April 2026; history 2026-04-17; catalog 2026-04-21 | 公開 PDF 已取得<br>僅 metadata | Summary/scope; headings only<br>USB2 electrical boundary catalog |
| USB-15 | [USB-IF Compliance Tools catalog](<https://www.usb.org/compliancetools>)<br>USB3CV 3.4.1.0 / XHCICV 3.3.0.0 / USBET20 2.20.00 as listed<br>USB3CV 2026-08-24; XHCICV 2026-07-28 | 公開目錄／頁面<br>目錄／入口已讀 | USB3CV；XHCICV；USB xHSETT；SigTest；USBET20<br>Find current CTS/tool entrypoints; no installation or execution |
| USB-16 | [USB-IF USB3.2 / USB2 compliance program and test matrices](<https://www.usb.org/usb-32>)<br>Catalog entrypoint<br>Checked 2026-10-13 | 公開目錄／頁面<br>目錄／入口已讀 | Test specifications / approved equipment<br>Scope/equipment screening only |
| USB-17 | [USB4 Specification](<https://usb.org/document-library/usb4r-specification-v20>)<br>Version 2.0<br>Catalog 2026-04-02; linked package November 2025 | 官方 metadata；本文存取未測<br>僅 metadata | 未讀本文；Deferred: only if USB4 router/tunnel events and product need established<br>Deferred: only if USB4 router/tunnel events and product need established |
| USB-18 | [USB Type-C Cable and Connector Specification](<https://www.usb.org/document-library/usb-type-cr-cable-and-connector-specification-release-25>)<br>Release 2.5<br>Catalog 2026-04-08 | 官方 metadata；本文存取未測<br>僅 metadata | 未讀本文；Deferred: only if CC/orientation/cable/attach evidence is in target scope<br>Deferred: only if CC/orientation/cable/attach evidence is in target scope |
| USB-19 | [USB Power Delivery Specification](<https://www.usb.org/document-library/usb-power-delivery>)<br>Revision 3.2 Version 1.2 (catalog)<br>Catalog 2026-09-14 | 官方 metadata；本文存取未測<br>僅 metadata | 未讀本文；Deferred: only if PD/CC decoded messages and a power-negotiation question exist<br>Deferred: only if PD/CC decoded messages and a power-negotiation question exist |
| USB-20 | [Intel xHCI specifications](<https://www.intel.com/content/www/us/en/products/docs/io/universal-serial-bus/universal-serial-bus-specifications.html>)<br>Rev1.2c and Rev2.0 listed<br>Catalog checked 2026-10-13; issue dates not verified | 1.2c PDF 已取得；2.0 fetch 失敗<br>僅 metadata | 1.2c cover/contents only<br>Deferred cross-layer register/TRB/host evidence; not field definition for LeCroy wire events |
| USB-21 | [USB Mass Storage Bulk-Only Transport](<https://www.usb.org/document-library/mass-storage-bulk-only-10>)<br>Revision 1.0<br>Catalog 1999-09-30 | 公開 metadata／PDF 入口；本文未讀<br>僅 metadata | 未讀本文；Deferred until interface protocol and BOT selection are observed<br>Deferred until interface protocol and BOT selection are observed |
| USB-22 | [USB Mass Storage UASP Bootability and Adopters Agreement](<https://www.usb.org/document-library/usb-mass-storage-class-specification-uasp-bootability-v10-and-adopters-agreement>)<br>Version 1.0<br>Catalog 2013-03-04 | 官方 metadata；本文存取未測<br>僅 metadata | 未讀本文；Deferred only if UASP boot path is a real requirement<br>Deferred only if UASP boot path is a real requirement |
| USB-23 | [T10 USB Attached SCSI / USB Attached SCSI-3](<https://www.t10.org/pubs.htm>)<br>INCITS 471-2010; INCITS 572-2021<br>UAS draft r04 2010-03-09; UAS3 r05 2020-11-07 | 公開目錄；final draft 受限未取<br>僅 metadata | 未讀本文；Deferred pending observed UAS interface and authorized source access<br>Deferred pending observed UAS interface and authorized source access |
| USB-24 | [USB Mass Storage Class Compliance Test Specification](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Cover Rev1.1; history Rev1.1a<br>2014-06-13 | 公開 bundle 已下載<br>僅 metadata | Cover/revision history only<br>Deferred conditional BOT/class tests |
| USB-25 | [UASP Testing for High Speed and SuperSpeed Devices](<https://www.usb.org/document-library/usb3cv-and-xhcicv-compliance-test-specifications>)<br>Rev0.9b<br>2012-06-06 | 公開 bundle 已下載<br>僅 metadata | Cover/revision history only<br>Deferred conditional UAS class tests |


### 本機 LeCroy 文件與原始範例（16）

| ID | 來源／版本／日期 | 取得與閱讀 | 已讀定位及適用限制 |
| --- | --- | --- | --- |
| LC-01 | [PETracerVSEManual.pdf](<C:/Program Files/LeCroy/PCIe Protocol Suite/Documents/PETracerVSEManual.pdf>)<br>PCIe Protocol Analysis 13.26; generated 2026-01-08<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | §5.2.2 DLLP；§5.2.3 TLP；§5.2.10 Link；§5.2.11 Split（PDF21–37）<br>Different event levels have different field applicability. Native split section contains Link-transaction wording; use named constants and verify runtime shape. |
| LC-02 | [PCIeAutomationManual.pdf](<C:/Program Files/LeCroy/PCIe Protocol Suite/Documents/PCIeAutomationManual.pdf>)<br>PCIe Protocol Analysis 13.26; generated 2026-01-08<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | BuildConfigurationSpace PDF340；ExportToText/2 PDF366–367/436；GetConfigurationSpace PDF461；PEConfigurationSpace PDF951+<br>ExportToText 受隱藏封包／range 影響；既有 sampled PASS 與 BuildConfigurationSpace 排除範圍保留。 |
| LC-03 | [PETracerFileBasedDecodingManual.pdf](<C:/Program Files/LeCroy/PCIe Protocol Suite/Documents/PETracerFileBasedDecodingManual.pdf>)<br>Installed file; PDF metadata 2026-01-08<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | Configuration Space discussion PDF76<br>File-based decode reference only. No renewed .pecfgdec/CFG.dec install scope. |
| LC-04 | [USBProtocolSuiteVSEManual.pdf](<C:/Program Files/LeCroy/USB Protocol Suite/Documents/USBProtocolSuiteVSEManual.pdf>)<br>Manual v9.12; USB Protocol Suite v10.13+; July 2025<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | LFPS PDF30–31；Link Command32；Transaction86–87；Transfer89；事件145/149；SendTransfer168；badCRC170；generic field171–174<br>LTSSM 無已確認 state member；completed=1 與 badCRC 預設會影響 coverage；USB2 PID 欄位不可直接套 USB3。 |
| LC-05 | [USBAnalyzerAutomationManual.pdf](<C:/Program Files/LeCroy/USB Protocol Suite/Documents/USBAnalyzerAutomationManual.pdf>)<br>Last update 2026-06-24; suite version not asserted by cover<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | ExportToText PDF112-113 / printed108-109；GetPacket PDF122-125 / printed118-121<br>GetPacket returns raw packet, not native transfer grouping. No TransferParser/GetTransfer API name found in installed manual text. |
| LC-06 | [USBScriptDecodeManual.pdf](<C:/Program Files/LeCroy/USB Protocol Suite/Documents/USBScriptDecodeManual.pdf>)<br>CSL Reference Manual; PDF metadata 2019-12-03<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | CSL decode functions / bit fields; general reference<br>No TransferParser name found; native transfer extraction is documented in VSE LC-04, not assumed here. |
| LC-07 | [VS_constants.inc](<C:/Users/Public/Documents/LeCroy/PCIe Protocol Suite/Scripts/VFScripts/VS_constants.inc>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | DLLP codes lines43-67; message codes201-220; named constants may be engine-defined/commented<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-08 | [VS_constants.inc](<C:/Users/Public/Documents/LeCroy/USB Protocol Suite/Scripts/VFScripts/VS_constants.inc>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | Link command values lines93-139<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-09 | [VSTools.inc](<C:/Users/Public/Documents/LeCroy/USB Protocol Suite/Scripts/VFScripts/VSTools.inc>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | ReportTraEventInfo389; ReportXferEventInfo528; GetLfpsDesc1003-1021; GetUsb3LnkCmdDesc1051; Report link1137-1140<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-10 | [zExampleXfer.vse](<C:/Users/Public/Documents/LeCroy/USB Protocol Suite/Scripts/VFScripts/Examples/zExampleXfer.vse>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | SendLevelOnly(_XFER), ReportXferEventInfo, GetDecodedScriptField/GetHexScriptField<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-11 | [zExampleTra.vse](<C:/Users/Public/Documents/LeCroy/USB Protocol Suite/Scripts/VFScripts/Examples/zExampleTra.vse>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | SendLevelOnly(_TRA), ReportTraEventInfo<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-12 | [zUsb3_Example.vse](<C:/Users/Public/Documents/LeCroy/USB Protocol Suite/Scripts/VFScripts/Examples/zUsb3_Example.vse>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | USB3 Link command raw fields around195-201<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-13 | [examp_link_transactions.pevs](<C:/Users/Public/Documents/LeCroy/PCIe Protocol Suite/Scripts/VFScripts/Examples/examp_link_transactions.pevs>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | SendLevelOnly(_LINK)61; in.TransactionStatus97<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-14 | [examp_split_transactions.pevs](<C:/Users/Public/Documents/LeCroy/PCIe Protocol Suite/Scripts/VFScripts/Examples/examp_split_transactions.pevs>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | SendLevelOnly(_SPLIT)61; in.CompletionStatus97<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-15 | [examp_dllps.pevs](<C:/Users/Public/Documents/LeCroy/PCIe Protocol Suite/Scripts/VFScripts/Examples/examp_dllps.pevs>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | Vendor DLLP example<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |
| LC-16 | [examp_ltssm.pevs](<C:/Users/Public/Documents/LeCroy/PCIe Protocol Suite/Scripts/VFScripts/Examples/examp_ltssm.pevs>)<br>Installed vendor source; exact file identified by SHA-256<br>文件日期見版本字串；查核 2026-10-13 | 本機來源已讀，非 runtime 證明<br>指定段落已讀 | Vendor PCIe LTSSM example<br>來源文件／範例；可用欄位仍須對實際 event level 驗證。 |


### OS／平台記錄參考（8）

| ID | 來源／版本／日期 | 取得與閱讀 | 已讀定位及適用限制 |
| --- | --- | --- | --- |
| OS-01 | [WHEA 0x124 error-source parameters](<https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x124---whea-uncorrectable-error>)<br>Microsoft documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Parameters / Remarks<br>確認 error-source 類型與記錄入口；0x124 本身不等同 PCIe 根因。 |
| OS-02 | [WHEA PCI Express error section](<https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_whea_pciexpress_error_section>)<br>ntddk.h documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Members: ValidBits, DeviceId, ExpressCapability, AerInfo<br>只解讀有效欄位；欄位存在不證明當次錯誤記錄含有效 PCIe 資料。 同頁另一筆：PCI-43。 |
| OS-03 | [WinDbg !errrec](<https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-errrec>)<br>Microsoft documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Parameters / example error record<br>離線錯誤記錄輸入參考；本輪未執行 debugger、未開 dump。 |
| OS-04 | [UEFI Common Platform Error Record](<https://uefi.org/specs/UEFI/2.11/Apx_N_Common_Platform_Error_Record.html>)<br>UEFI 2.11 Appendix N<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | N.2.1 / N.2.2 / N.2.7 Table N.34<br>適用 record revision 與 ValidBits 須核對；collection timestamp 不一定是錯誤发生時刻。 |
| OS-05 | [USB Event Tracing for Windows](<https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-event-tracing-for-windows>)<br>Microsoft documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | USB ETW support: Hub3 / UCX / xHCI<br>用於 Host 軟體層觀察；不能當成 USB 線上每個封包或電氣證據。 |
| OS-06 | [USB ETW activity IDs](<https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/using-usb-etw>)<br>Microsoft documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Activity ID association across providers<br>OS 事件可依 Activity ID 關聯；不能直接等同 CATC packet 或跨來源時間同步。 |
| OS-07 | [Linux usbmon](<https://docs.kernel.org/usb/usbmon.html>)<br>Kernel documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | Introduction / Text API / Binary API<br>HCD request-level 觀察可能不精確等同 bus transaction；不供 LFPS/電氣判定。 |
| OS-08 | [Linux PCIe AER guide](<https://docs.kernel.org/PCI/pcieaer-howto.html>)<br>Kernel documentation; retrieved 2026-10-13<br>文件日期未另確認 | 公開本文已取得<br>指定段落已讀 | 8.1 / 8.2 / 8.3<br>AER severity、status/mask、header 與 recovery 的補充實作；不替代 PCI-SIG 條款或 Windows 行為。 同頁另一筆：PCI-41。 |


## 重複與 bundle 計數

OS-08／PCI-41 是同一份 Linux AER 頁面的兩筆閱讀紀錄；OS-02／PCI-43 是同一份 WHEA PCI Express error section。保留 ID 可追溯原研究，不能計成兩份獨立規範。USB 多個 source ID 也共用 bundle／library URL，但代表 package、不同子文件或不同閱讀範圍；JSON 的 `duplicates_and_shared_entrypoints` 明列其關係。

| Bundle inventory parent | 成員筆數 | 已做與未做 |
| --- | ---: | --- |
| USB-02 | 18 | USB3.2 ECN／Appendix E redline 的檔名、檔案 hash 與入口；不等於每份內容已讀或每項變更仍需套用。 |
| USB-04 | 34 | USB2 ECN／errata／supplement 清單，未把 base 與 adopter agreement 重算；各檔版本／日期未全數轉錄。 |
| USB-07 | 14 | USB3CV／XHCICV package 內 PDF 清單；USB-08–11、24–25 另有 document-level 閱讀紀錄，兩層不能相加當獨立全文。 |

66 筆成員均列為 inventory／metadata_only。部分子文件另有已讀章節，應查其 top-level source row；不能把 parent bundle 的下載狀態套成每份本文已讀。

## 研究停止條件與後續用途

本輪已盤點本案所需官方規範／ECN／test 家族，對會改變第一批 slice 的公開或本機正文讀到具體章節，並登錄未取得、未讀與版本相依的來源。這已足以切出有邊界的 probe、adapter、evaluator；沒有宣稱全網或歷史版本已窮盡。

需要完整 timing／compliance verdict 的規則，仍須取得適用版本正文、確認 errata／ECN 優先關係、capture 前提與獨立 fixture。USB4／Type-C／PD、storage class、xHCI register／TRB、electrical 等分支，只有在產品範圍和觀測資料相符時才展開。沒有因此執行測試、提交存取表單或改變先前的 scope 排除。

TEMP 下載與文字提取只是本輪研究中介檔，不是耐久交付來源；JSON 保留其 provenance，但查核應回到官方 URL 或本機原檔路徑與 SHA。此文件與 JSON 只收研究索引及自行撰寫的摘要，不納入標準 PDF、vendor 原始檔或其全文。下一步由 [slice 計畫](pcie-usb-spec-slices-20261013.md) 固定依賴、最小輸入與驗收。
