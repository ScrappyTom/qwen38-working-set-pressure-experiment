# Execution of the prepared uncoached contribution

The owner said "Proceed" after the explicit recommendation to run the prepared
task once with at most 16 requests and 24 operations. This authorizes execution
of the separate run-001; the earlier preparation-only statement stays preserved.

Implementation: c476ee9d8a31f12438697ab572338b9cbf928ee7. The workspace was clean at
launch. Manifest SHA-256:
3c88c6efd60e2e7d5c9c64758c99ac5e40b6a2bac465aa05cb5758e65cc59ae0.
Preparation seal SHA-256:
20944764c10a57147c9e45c0fd82284dbaf568defd496b6b7193295ee9ac9080.

The existing runner verified the sealed package and bound sources before reserving
the attempt. It launched the owned q4/56,576 runtime with no MTP and unchanged
thinking on/xhigh/uncapped settings, sampling and advisory GPU-memory policy.
The actual first wire request is byte-identical to the prepared request at
3,775 native input tokens. No runtime coaching, source hint, factual correction
or public-discussion feedback is introduced. Review files are outside the host's
decision inputs. There is no retry or use of previously closed allowances.

The run is now closed with checked_submission. Reservation was recorded at
2026-09-13T23:42:41.535171+00:00; task closure at
2026-09-14T00:36:02.242160+00:00 and runtime closure at
2026-09-14T00:36:04.213974+00:00. These are UTC; the local execution date was
September 13. Four requests returned complete responses and executed five actual
operations. The unused 12-request / 19-operation allowance is closed, not a
continuation entitlement. No stop, rescue, corrective dialogue or changed setting
occurred during execution.

The actor is Qwen3.8-27B UD-IQ3_XXS with q4_0 K/V, physical context 56,576, no MTP,
thinking on/xhigh/uncapped and request seed 961207. All four actual requests retain
the same sampling and cache-off configuration. The 23,808-token input limit and
32,768-token prospective generation reserve were unchanged. C03 exceeded the
reserve; this is recorded, not capped or relabeled as a failed admission.

The exact final candidate is
baa81a49475c59f1686de781ef396e6709d7efb1cb31eec62992576790b2ab84.
Only Lib/test/test_configparser.py changes. The current public check passes on
that candidate and checker definition, and submission identifies the same version.

The [response seal](../run-001/RESPONSE_SEAL.json) has SHA-256
95335757c598d456359689897a6454376f9253dfdb74872259bfac8b28400912.
Its 107-file inventory aggregate is
9d8a3ff3c6743e523794d4cb0f5bd237571ade1286a413084a56c5a789be7d7c.
All 94 chained records, 107 inventoried files and 240 bound source identities were
verified. All three local private-runtime hashes match; private paths and runtime
logs remain excluded from version control. The original record verifies owned
runtime shutdown and the free dedicated port. Telemetry contains 15,331 samples,
with a 163 MiB minimum free GPU memory. No CUDA failure or context truncation was
observed. This remains monitored operation under the owner's existing advisory
policy, not a pass of the historical 350 MiB target.

Exact offline replay was executed after closure:

```powershell
$env:PYTHONPATH = 'src;tests;scripts'
py -3.12 -B -X utf8 scripts/verify_uncoached_contribution.py development/uncoached_contribution/run-001
```

It reconstructed six native inputs, replayed all four replies / five operations,
re-executed the actual checker, reproduced intermediate snapshots and reached the
same submitted candidate. The verifier returned
native_inputs_reconstructed_operations_replayed with model_requests=0. Zero means
no model inference during replay; the actual execution used four requests.

The additional saved-evidence check can be reproduced with:

```powershell
$env:PYTHONPATH = 'src;tests;scripts'
py -3.12 -B -X utf8 development/uncoached_contribution/review/verify_saved_evidence.py
```

This checks custody, unchanged request settings, actual source/receipt delivery,
artifact preservation and recorded metrics. It sends no completion requests and
does not execute the checker again. Its [verification](VERIFICATION.json) and
[metrics](METRICS.json) are review products outside the sealed raw attempt.
No production code changed during this turn; the earlier 58 selected preparation
tests were not presented as a newly rerun full suite.

Model requests take 3,159.796 seconds; the task loop takes 3,171.781 seconds.
Response processing including native admission takes 5.217 seconds across four
replies and is included in the task-loop time. The remaining task-loop difference
also includes lifecycle checks and recording. These are not a complete measure
of development, Codex inference or reviewer effort. Full direct review is done,
but reviewer labor and Codex token use were not separately instrumented.
