# Saved-report run 001: artifact audit

The closed run saved a correct two-build incident report, preserved the supplied optimizer repair and submitted the actually checked final candidate. The first contribution also remained intact through the declared restart and the later extension. The live check failure was incomplete report coverage, not a wrong first entry or malformed JSON.

This audit directly inspected the saved candidate versions, both actual report edit arguments and results, all six actual wire inputs, the full capture bodies present in those inputs, inherited custody and both current check receipts/streams. The report comparisons below were independently derived with the existing safe captured-AST decoder and source/field-order traversal, without executing the optimizer, checker, model or native runtime. The grader's `EXPECTED_REPORT` was not used to derive the comparison. Checker source was inspected separately to establish its scope and gate order. Exact operation replay and its reconstruction issue are separate from this artifact assessment.

## Exact work and preservation

The starting repaired candidate is `f7939c49b60d57f19b88dde8d31c6deb0ea036b6a3746c5d27b61d5ce0b99fd6`, supplied through the historical reviewer-executed repair and three inherited records. It is not the newer compiler run-003 candidate. The only files edited by the current actor are the two revisions of `reports/incident.json`.

| Saved work | Candidate | Report bytes | Report SHA-256 |
| --- | --- | ---: | --- |
| Supplied repair, empty report | `f7939c49...` | 15 | Historical starting version |
| C01 first contribution, OBS-0002 only | `f977a547b1abe113f61f3831ab8832cdc8a89c40ca21d89eece252220f5a3a08` | 179 | `ab0fba0714e4b221f2d913f8814da1494aab90f5fb9d243c6be4a35c3ea8c36f` |
| C04 complete contribution | `d05c7ed89f9de61f67872faeb06c84688a02f68134eb40bbf5db889c6c08204b` | 363 | `70134ded9f3d120a68f72ed16f94fcd14c93c12a60b003334753898ae0b8bbca` |

At both newly saved candidate versions, all five nonreport files have exactly the supplied candidate's paths and bytes: `README.md`, `compiler/__init__.py`, `compiler/api.py`, `compiler/selection.py` and `compiler/unary.py`. This includes the existing repair's exact built-in numeric-type unary-plus guard. The original defective version is separately retained in source history; it is not confused with the supplied repair when checking preservation.

C03's actual post-restart input contains the exact 179-byte first report. C04 replaces only its closing suffix to append the second entry. The entire existing first entry remains textually unchanged, and its parsed object is identical in the final report. No later acquisition, account or check changes either report revision or any compiler file.

The exact final report, followed by one newline, is:

```json
{"builds": [{"capture": "OBS-0002", "changed_functions": ["_normal_dist_inv_cdf"], "first_change": {"function": "_normal_dist_inv_cdf", "before": "-log(r)", "after": "log(r)"}}, {"capture": "OBS-0003", "changed_functions": ["_normal_dist_inv_cdf", "weibullvariate"], "first_change": {"function": "_normal_dist_inv_cdf", "before": "-log(r)", "after": "log(r)"}}]}
```

## Comparison against the actual historical evidence

The immutable input and build captures remain bound to original candidate `28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d`:

| Capture | Exact body bytes | Exact body SHA-256 |
| --- | ---: | --- |
| OBS-0001, original module | 9,228 | `a46074dc3b63c6e2d05a82e6e2b9456504ad1265719a062fea2a3a1b437c65ed` |
| OBS-0002, BUILD-A | 9,168 | `b4fb8213b1f34119d324b665faeb2a7d070e47633620a15049c13ca2b237863e` |
| OBS-0003, BUILD-B | 9,180 | `53c22eefe174b759fec309e18bc29f520748694dc9a06aafb7eb216f729c868a` |

Comparing complete top-level function ASTs with the original yields only `_normal_dist_inv_cdf` for OBS-0002, and `_normal_dist_inv_cdf` followed by `weibullvariate` for OBS-0003. Traversing those functions in source order and their fields in normal AST order identifies the same first expression-node-kind change in both builds: the original `UnaryOp(USub, Call(log, r))` becomes the emitted `Call(log, r)`, expressed as `-log(r)` to `log(r)`. The enclosing `sqrt(...)` remains a call; the changed expression is not a numeric constant. These independently derived values match every saved report field.

The actual C01 input provides complete OBS-0001 and OBS-0002 bodies, sufficient to derive the first entry; OBS-0003 has an inventory address but no body. At restart C03 provides complete OBS-0001 and OBS-0003, the actual failed current check and the exact saved report, with OBS-0002's body absent. Qwen's C03 acquisition brings back OBS-0002 exactly. C04, C05 and C06 then contain all three complete historical bodies together. Every delivered capture body compared byte-equal to its sealed imported original; this finding does not rely on `shown_complete` labels alone. No actual wire input contains `EXPECTED_REPORT` or an evaluator-authored reference contribution.

The captures describe builds before the supplied repair. Their recovery does not execute those builds again, establish current check applicability, or authorize source editing. The report accurately describes that historical incident; it does not assert that the repaired current candidate emitted the faulty trees.

## Actual verification and its limits

C02 explicitly checks the first report candidate `f977a547...`. CHK-0009 executes the registered public checker `23d69d6a42e0f8bfd34ac0ea83c14e533ab549cae67d9755b3f0126f2e39446a`, completes with return code 1, preserves complete stdout and empty stderr, and returns:

```text
FAIL incident report agrees with captured builds: AssertionError: report must cover each emitted capture exactly once
25/26 contract cases passed
```

The report case checks that every emitted capture occurs exactly once before comparing per-entry values. Therefore that failed check does not establish the correctness of the saved first entry. Its correctness is established here by the independent capture comparison. The first check's failure identifies the remaining build obligation, not an incorrect first-entry expectation. This live run does not demonstrate correction of malformed JSON or an experimentally refuted report value.

C05 explicitly checks the actual final candidate `d05c7ed89...`. CHK-0017 uses the same checker definition, completes with return code 0, preserves the exact 29-byte stdout `26/26 contract cases passed\r\n`, and has empty stderr. C06 receives that applicable final-candidate pass and submits the same unchanged candidate. The earlier failed check is correctly inapplicable after the C04 edit; the inherited flat RES-0003 receipt remains historical and carries no newly invented observation/check-definition authority.

The 26-case public scope combines twenty-five optimizer-contract cases with one report case. The latter validates the complete capture set, changed-function ordering and equivalent before/after expression ASTs. It does not validate every informal narrative claim, every future input or the semantic usefulness of a working account. There are no injected fault tests in this task. The host's checked-submission gate is a protection; the actor's separate check request and later use of its actual result remain the behavioral evidence.

## Classification and closure

This is an assisted, reused-task, two-phase saved-work continuation without live coaching. Prescribed initial/restart acquisitions and the supplied repair remain assistance dependencies. The actor independently writes both report contributions, requests both current checks and obtains the truly absent historical counterpart after restart. It does not independently select the initial groups, repair the optimizer anew, recover from genuine input pressure or correct a wrong report entry.

The only account is a closing account in C06, after the final pass was available. It correctly describes the preserved repair, completed report and passing check, but no subsequent decision consumes it. This establishes accepted closing-account use, not continuity benefit from a saved interim interpretation.

The closed metrics reconcile six requests, seven actor operations, nine new assisted operations and three inherited operations. They record 23,009 generated tokens, 116,256 input tokens, 1,591.266 model-request seconds and 1,629.360 task-loop seconds. Peak sent input is 22,301 tokens; maximum input plus generation is 27,512. No output exceeds the declared reserve, and no rejection or runtime truncation occurs. These totals describe this assisted configuration, not a controlled performance comparison.

The response-seal file SHA-256 is `8e0c0c553dd3fbe16c2ed4a07ac82cb5445ffa254e2a56b8b7c13e4e5e7afa86`; its file-inventory aggregate is `bded244e0e7b1407b3f7e790cf4ede8162925de6baa5fc05353d21c4be87f6ec`. The original exact replay reached the final checkpoint comparisons but failed the final restore roundtrip on integer-versus-string diff-map serialization order; see `RESTORE_FINDING-001.md`. That post-closure apparatus defect must remain disclosed and separately repaired. It does not change the independently compared artifact bytes or the actual check observation, and this audit does not label the original whole replay as passed.
