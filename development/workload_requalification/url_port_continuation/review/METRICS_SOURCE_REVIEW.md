# Pre-freeze metrics review

The independent read-only review found two terminal-shape handling gaps in the evaluator metrics helper, before any continuation run or full replay/metrics execution:

* An endpoint response could have ordinary numeric usage and non-dictionary cache details. The helper now retains unavailable cache data as `None`; it does not manufacture zero.
* Negative generation could satisfy token arithmetic and enter aggregate cost. After root authorization, the helper now requires nonnegative prompt tokens, positive integer completion tokens, correct arithmetic, the actual dispatched prompt count and the 56,576-token physical ceiling. Unusable usage remains unavailable.

The source before the second correction is preserved exactly in `metrics-review/measure_run-before-usage-boundary.txt`, SHA-256 `44f7e5fd2acb5e6488c084c4d805cb6296cbdbbb5b98c41bb5f5f9398d720966`. The correction changed evaluator accounting only; the production host, task, original run and prospective model input were not changed.

`METRICS-USAGE-CPU-001.log` records the first CPU qualification: eleven saved-response fixture cases passed, including missing/list cache details, negative/zero/boolean completion values, exact physical boundary, overflow, prompt mismatch and non-dictionary usage. Temporary files contained only invented response shapes; no model, checker, native or tokenization operation executed. This is robustness qualification of accounting, not new workload evidence.

The independent original-checkpoint smoke separately passed on its first attempt in `REPLAY-SMOKE-001.log`. Full replay and cost accounting remain prohibited until the continuation run has closed and the parent authorizes post-run inspection.
