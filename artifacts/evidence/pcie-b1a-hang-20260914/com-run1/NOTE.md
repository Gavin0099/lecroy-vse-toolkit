# B1a COM run 1: parse error (failed, kept as history)

- Script deployed at SHA-256 `7FAB3B89984ED5A75303E532357CE0A727A15F5B2F427BFA001ABE015A4C5EEF`.
- 18:00:00 `OpenFile` returned (19.3 s); `LaunchVScript` returned.
- PETracer showed a modal `PCIe Protocol Analysis` dialog: "Parse Error : Error in file
  '...\b1a-link-fields.pevs' at line 46 : parse error, unexpected '-'". Line 46 was
  `set PrevS0_1 = -1;`: VSE does not accept a negative literal in a global `set`.
- The runner at that time had no dialog handling and kept waiting. The dialog was found by
  read-only window enumeration at 18:07 and dismissed by BM_CLICK on its OK button at
  18:08:23.482; a second identical dialog was dismissed at 18:09:52.373. These two clicks were
  cleanup input sent from outside the runner, so `com-run.json` still says
  `input_sent_to_gui: none`; that field is wrong for this run.
- `OnVScriptFinished` then arrived with result `-3`, which the manual names
  `FEATURE_NOT_LICENSED`; here it followed a parse error, so the code is not evidence of a
  licensing problem. The captured report text contains the parse error and a "Runtime Errors"
  block.
- Status `COM_RUN_FAILED`; converted copy, original and read-only copy identities unchanged;
  PETracer exited after `Close`.

Fixes: the not-yet-seen sentinel is now 1000 (script SHA-256 `E314B6B5...`), and
`com_run_vse.py` now detects PETracer error dialogs, records their text, dismisses them as
recorded cleanup input and fails the run.
