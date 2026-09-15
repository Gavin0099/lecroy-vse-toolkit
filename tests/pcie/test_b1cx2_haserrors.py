import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))

import verify_b1cx2_haserrors as x2

HEADER = "PCIE_B1CX2_HASERRORS_V1 start=100 end=400 r1_end=200 r2_end=300 cap=2"


def make_log(mutate=None, done=True):
    # R1: 50 events on C2, no errors. R2: 30 events on C2, 30 TS1 all HasErrors via ErrorAllignment. R3: 20 on C1, 5 unexplained.
    scopes = {"R1": [50, 40, 0, 0, 0], "R2": [30, 30, 0, 30, 0], "R3": [20, 10, 5, 5, 5],
              "C1": [20, 10, 5, 5, 5], "C2": [80, 70, 0, 30, 0], "C3": [0, 0, 0, 0, 0]}
    cells = {(1, 2): [50, 40, 0], (2, 2): [30, 30, 30], (3, 1): [20, 10, 5]}
    flagset = {("R2", "ErrorAllignment"): 30, ("C2", "ErrorAllignment"): 30}
    samples = ["PCIE_B1CX2_SAMPLE|250| 9.580 sec|Downstream|2|2|5|2|2.0|ErrorAllignment,",
               "PCIE_B1CX2_SAMPLE|251| 9.580 sec|Downstream|2|2|5|2|2.0|ErrorAllignment,",
               "PCIE_B1CX2_SAMPLE|350|10.912 sec|Upstream|1|3|5|2|2.0|NONE",
               "PCIE_B1CX2_SAMPLE|351|10.912 sec|Upstream|1|3|5|2|2.0|NONE"]
    state = {"scopes": scopes, "cells": cells, "flagset": flagset, "samples": samples,
             "end": "PCIE_B1CX2_END|events=100|has_errors=35|unexplained=5|reason=trace_end",
             "heevent": "PCIE_B1CX2_HEEVENT|tlp=0|dllp=0|ordered_set=35|other=0", "extra": []}
    if mutate:
        mutate(state)
    lines = [HEADER, *state["samples"], *state["extra"]]
    lines += [f"PCIE_B1CX2_PRESENT|{f}={100 if f != 'FCError' else 0}" for f in x2.FLAGS]
    lines += [f"PCIE_B1CX2_SCOPE|{s}|" + "|".join(map(str, v)) for s, v in state["scopes"].items()]
    lines += [f"PCIE_B1CX2_FLAGSET|{s}|{f}={state['flagset'].get((s, f), 0)}" for s in x2.RANGES + x2.CHANNELS for f in x2.FLAGS]
    lines += [f"PCIE_B1CX2_CELL|{r}|{c}|" + "|".join(map(str, state["cells"].get((r, c), [0, 0, 0]))) for r in (1, 2, 3) for c in (1, 2, 3)]
    lines += [state["heevent"], state["end"], ""]
    if done:
        lines.append(x2.DONE_MARKER)
    return "\n".join(lines) + "\n"


B1B = {"window": {"start": 100, "end": 400}, "totals": {"events": 100, "err_any": 35}}


class B1cx2Tests(unittest.TestCase):
    def test_accepts_consistent_output(self):
        result = x2.parse(make_log(), B1B)
        self.assertEqual(result["flags_set"]["ErrorAllignment"]["R2"], 30)
        self.assertEqual(result["channel_names"], {"C1": "Upstream", "C2": "Downstream"})
        self.assertEqual(result["samples"][0]["flags"], ["ErrorAllignment"])
        self.assertEqual(result["samples"][2]["flags"], [])

    def test_rejects_totals_that_do_not_close(self):
        def bad_scope(s):
            s["scopes"]["R1"][0] = 51
        with self.assertRaisesRegex(x2.B1cx2Error, "events over R scopes"):
            x2.parse(make_log(bad_scope))
        def bad_flag(s):
            s["flagset"][("C2", "ErrorAllignment")] = 29
        with self.assertRaisesRegex(x2.B1cx2Error, "range and channel totals differ"):
            x2.parse(make_log(bad_flag))
        def bad_cell(s):
            s["cells"][(2, 2)] = [30, 30, 29]
        with self.assertRaisesRegex(x2.B1cx2Error, "cell"):
            x2.parse(make_log(bad_cell))
        with self.assertRaisesRegex(x2.B1cx2Error, "differ from B1b"):
            x2.parse(make_log(), {"window": {"start": 100, "end": 400}, "totals": {"events": 100, "err_any": 36}})

    def test_rejects_bad_samples(self):
        def outside(s):
            s["samples"][0] = "PCIE_B1CX2_SAMPLE|150| 9.580 sec|Downstream|2|2|5|2|2.0|ErrorAllignment,"
        with self.assertRaisesRegex(x2.B1cx2Error, "outside range"):
            x2.parse(make_log(outside))
        def too_few(s):
            s["samples"].pop()
        with self.assertRaisesRegex(x2.B1cx2Error, "samples, expected"):
            x2.parse(make_log(too_few))
        def two_names(s):
            s["samples"][1] = "PCIE_B1CX2_SAMPLE|251| 9.580 sec|Upstream|2|2|5|2|2.0|ErrorAllignment,"
        with self.assertRaisesRegex(x2.B1cx2Error, "more than one channel name"):
            x2.parse(make_log(two_names))

    def test_rejects_runtime_error_and_missing_done(self):
        with self.assertRaisesRegex(x2.B1cx2Error, "runtime-error"):
            x2.parse(make_log(lambda s: s["extra"].append("script error at line 12")))
        with self.assertRaisesRegex(x2.B1cx2Error, "completion marker"):
            x2.parse(make_log(done=False))


if __name__ == "__main__":
    unittest.main()
