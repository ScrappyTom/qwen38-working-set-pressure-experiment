# Compiler entry run 003: independent artifact audit

## Scope and result

Reviewed after `run-003/RESPONSE_SEAL.json` was present. The run closed normally with `checked_submission`, final candidate `c2866b765306e1e38516d48aeacdeb304023aa0796e0781c5d33ecec904c56e2`. This audit directly examines the starting/final file bodies, original task and README contract, immutable capture bodies, actual C11–C14 wire inputs, complete C11–C14 thinking and final replies, operation receipts, and preserved CHK-0019 streams/outcome. It does not substitute a scripted route for the actor's operations.

The saved optimizer repair is correct for the supported parsed Python literal behavior reviewed here, and the incident report correctly compares both historical emitted modules. Actual public verification passed on that exact final candidate before submission. Only the two authorized target files changed. One narrow malformed-AST boundary remains: the numeric guard is broader than the account's description of it as an *exact* built-in type predicate. The distinction and executed probe are recorded below; no normal parsed-literal failure was found.

Post-closure CPU probes use Python 3.11.4 and the exact saved package in a temporary directory. They are reviewer evidence, not additional model outcomes, acceptance cases, or a rerun of the public checker. The executable probe and results are `artifact_probe_003.py` and `ARTIFACT_PROBES-003.json` in this directory. No model/checker rerun, frozen-source change, or repair to the saved artifact was performed.

## What actually became saved work

| Response | Requested operation and actual effect |
| --- | --- |
| C11 | Guarded patch of `compiler/unary.py`; accepted successor `ba4ab41a26fa7d26398bb4739359a635fdb885235a979092deef80c6a757f972`. |
| C12 | Account update and guarded patch of `reports/incident.json`; accepted final candidate `c2866b765306e1e38516d48aeacdeb304023aa0796e0781c5d33ecec904c56e2`. |
| C13 | Model-requested public check of the final candidate; actually executed as CHK-0019, returned pass. |
| C14 | Model-requested submission of the same checked candidate; accepted. |

The final file set is identical to the starting set. Exact UTF-8 bodies of `README.md`, `compiler/__init__.py`, `compiler/api.py`, and `compiler/selection.py` remain unchanged. The probe independently recomputes each final file's recorded SHA-256. Changed file hashes are:

- `compiler/unary.py`: `a580a18f5ec373767721681e32b16c16916c861eadc884facddc14873bc38beb`.
- `reports/incident.json`: `70134ded9f3d120a68f72ed16f94fcd14c93c12a60b003334753898ae0b8bbca`.

## Information supporting the decisions

The actual C11 input contains the complete current README, API, selection implementation, unary implementation, and one-line initial report. It also contains all three full imported captures as exact selected RES bodies. C12–C14 retain all three exact captures. This conclusion is based on decoding the actual shown bodies, checking their byte lengths and digests, and comparing their contents with the sealed originals, rather than trusting the inventory's `shown_complete` flags alone.

The C11 source bodies are bound to the original candidate. C12's current source bodies have been refreshed to the optimizer-patch successor, including the complete 15-line repaired unary implementation; the one-line report is still the initial empty report. C13 and C14 show both saved changes bound to the final candidate. In every one of these inputs the capture receipts remain bound to original historical candidate `28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d`. The evidence did not become a claim that the repaired candidate produced those old builds.

Qwen's C11 and C12 complete responses inspect the actual differences: the removed minus around `log(r)`, the later `x = -x` change, and the additional Weibull change in BUILD-B. They resolve the report to the changed subexpression, rather than the enclosing `sqrt(...)` call or whichever function supplied the recorded behavior. C13 revisits the same distinction before requesting execution. These outputs support the report's meaning; the public checker is not the sole basis for this audit.

The working account preserves the bug, intended fix, report comparisons, and pending check/submission. Its phrase “exact built-in” is stronger than the `isinstance` predicate actually proposed. The final C14 reasoning also loosely describes the old bug as folding the call into a constant; the actual old code removed its operator and retained the Call. These narrative inaccuracies do not change the saved patch/report or the candidate used for execution and submission. They should not be silently upgraded into accurate source descriptions.

## Optimizer correctness and limits

The original transformer stripped both unary plus and unary minus from every operand, including names and calls. The saved repair only folds an operand that is an `ast.Constant` with an integer/float value excluding bool. Required plus folding returns that literal. Optional minus folding constructs the negated constant. Names, calls, boolean constants, complex constants, and other operands retain their operators; generic traversal still visits their children.

For exact built-in integer and float constants, literal negation has no user dispatch and preserves the runtime value/type, including the sign of floating zero. Optional minus folding is allowed by the README, so differing from the preparation's plus-only reference patch is not a defect. Unchanged API and selection code retain deep copying, selected-function scope, unknown-name rejection, and unchanged nonselected/module-level structure.

The narrowly relevant reviewer comparisons execute 16 parsed expressions before and after optimization. They cover boolean plus/minus and nesting, signed floating zero and nested signs, complex literals, numeric nesting, inversion, and `not`; value, exact result type, and zero sign match in every comparison. The input AST remains unchanged in these probes. A separate runtime numeric-subclass example retains both custom `__pos__` and `__neg__` calls and their results. These checks address consequences of this patch; they are not an exhaustive proof for all Python syntax.

**Malformed caller-created AST limitation.** `isinstance(value, (int, float)) and not isinstance(value, bool)` is not equivalent to `type(value) in (int, float)`. A caller can manufacture `ast.Constant(IntSubclass(3))` inside a Module. Python compilation rejects that original Constant (`got an invalid type in Constant: I`), whereas the saved minus-folding branch invokes the subclass's `__neg__` during optimization and can produce an ordinary accepted Constant. The probe records the dispatch and changed outcome. Parsed Python literal source cannot produce this Constant payload; the same subclass supplied as a normal runtime operand retains its operators and dispatch. This therefore does not establish a failure on the supported valid literal/source path. It does prevent claiming that the implementation uses an exact-type predicate or that arbitrary malformed Module payloads have been qualified. If the API is intended to preserve rejection/dispatch for every caller-manufactured AST, this is a remaining boundary to resolve prospectively, rather than an invisible post-run artifact repair.

## Incident report comparison

An independent recursive comparison of the full captured ASTs, obtained from the actual C12 input, finds:

| Capture | All changed top-level functions, in source order | First expression whose node kind changed |
| --- | --- | --- |
| OBS-0002 / BUILD-A | `_normal_dist_inv_cdf` | `_normal_dist_inv_cdf`: `-log(r)` → `log(r)`, UnaryOp → Call. |
| OBS-0003 / BUILD-B | `_normal_dist_inv_cdf`, `weibullvariate` | `_normal_dist_inv_cdf`: `-log(r)` → `log(r)`, UnaryOp → Call. |

The saved JSON matches that result exactly. The enclosing `sqrt(-log(r))` remains a Call and therefore is not the requested node-kind change. BUILD-A's Weibull function remains structurally unchanged; BUILD-B changes it too. BUILD-B's recorded call to Weibull does not make its first source-order change occur there. Selection metadata is consistent with these findings, but actual whole-module AST comparison establishes which functions changed.

The captures also record the original real results, BUILD-A's `ValueError: math domain error`, and BUILD-B's complex result. Those observations concern the historical incident. The report neither changes the capture bodies nor claims they execute the repair.

## Actual verification and closure

CHK-0019 preserved outcome records `executed=true`, `termination=completed`, return code 0, `capture_complete=true`, the exact final candidate above, and original public-check definition SHA-256 `23d69d6a42e0f8bfd34ac0ea83c14e533ab549cae67d9755b3f0126f2e39446a`. Its complete 29-byte stdout is `26/26 contract cases passed\r\n`; stderr is empty. This checker contains ordinary behavioral acceptance and the historical-report case, with no injected faults. The pass is not a statement that a fault-detection experiment succeeded.

C14's actual input contains that current applicable passing observation and marks submission eligible. Qwen then submits the same candidate. Host enforcement protects applicability, while the observed action order supplies behavioral evidence that Qwen requested real verification after saving both targets and consumed it before closing.

This is a complete uncoached local contribution with a correct historical report and supported optimizer repair. It does not prove a general continuation policy, universal AST validation, context-pressure recovery, or an isolated causal effect of the retention change. The retention mechanism did, however, deliver the complete comparison material together throughout the exercised editing/checking/closure path, which the preceding stopped attempt did not do.
