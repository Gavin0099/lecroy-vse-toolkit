# PCIe-B2b：Config Access Log 契約

輸入為已通過 B2a 的 fields.json 與同一 capture 的 G2a 全 TLP metadata。
重新核對 B2a bytes／coverage；從全部 TLP 依 RequesterId／Tag 保留 pending
request，避免過濾掉 MRd 後錯配其 CplD。沿用 G2b type constants／BDF helper，
不沿用其不關閉 request 的候選配對。對向、target 相符且形狀完整的 config
completion 會關閉 request；之後無 pending request 的 Completion 保留未配對。
Memory split completion 完整性仍未建立，不更改舊 G2b 的歷史結果。

每筆 CfgRd／CfgWr 保留 time、packet、requester 與 target BDF、byte offset、
first／last byte enable、write payload 或 read returned value、completion packet／status。
CfgWr 為 request 意圖，不直接當 hardware state；CfgRd value 只有單一、對向、
目標 CompleterId 相符、成功 4-byte CplD 才可引用。重用未完成 key 的 request
與其後繼均不給確定 read value。失敗／缺失／多筆／錯形狀 completion 保留原記錄。
此 capture 的 read 皆全 DWORD；非 0xF first BE 的 read 本版留 UNKNOWN。

Association 有 trace 範圍與 Tag reuse 限制，不叫規範完整性驗證或 timeout。
0x940h[1] 未有 register decode 契約，不解碼、不從其他 offset 猜 MUX write。
切換時間以使用者／B1d context 來源的 anchor 明確輸入；before_disconnect、
disconnect_interval、after_reconnect 各自保留，絕不把舊 BDF state 帶到 SDE。

驗收：正向 read/write、partial write masks、非 config CplD 排除、錯 target／失敗
completion 不補值、Tag collision、不完整 coverage／hash 拒絕、真實重播兩次一致。

## 2026-10-02 review closure

Every still-pending requester/tag collision marks both requests ambiguous, including
requests with unqualified Completion candidates. Such candidates do not establish a
returned value or retire a key. Locked Completion types 19/20 not probed by B2a keep
metadata with `field_status=NOT_CAPTURED_BY_B2A`; no payload/register data is inferred.
They remain candidates or unmatched observations and do not close the pending key.

A reused key with existing unqualified candidates reports
`PENDING_KEY_REUSED_WITH_UNQUALIFIED_COMPLETIONS`. The legacy before-any-Completion
outcome applies only when the earlier request has no candidates.
