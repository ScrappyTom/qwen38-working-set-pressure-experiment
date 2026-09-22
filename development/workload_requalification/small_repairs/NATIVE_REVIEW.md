# Native preparation review

22 September 2026. Ran `run_repairs.py prepare <case> --version 001` sequentially
for artifact_map, shift and receipts after the interpolation runtime closed.
All three commands exited 0. No source or implementation was changed, no retry
was needed, and no model completion request was sent. Each owned runtime closed
before the next began; the final listener check found no listener on port 18124.

| Case | Initial input tokens | Baseline feedback | Source | Edit feedback | Successor-check feedback | Submission feedback | Minimum free GPU MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| artifact_map | 4,289 | 6,156 | 5,887 | 6,269 | 6,305 | 5,818 | 431 |
| shift | 4,346 | 5,770 | 5,776 | 6,116 | 6,384 | 5,902 | 431 |
| receipts | 4,335 | 6,097 | 5,928 | 6,231 | 6,430 | 5,894 | 431 |

These are native rendered/tokenized inputs against the 23,808 ceiling. They do
not qualify arbitrary broader acquisitions or bound future model generation.
There were six distinct measured inputs per case and five scripted operations,
not six or five Qwen calls. Memory samples numbered 79, 79 and 80. All closure
records show the expected context, full GPU offload, q4 K/V, MTP disabled, no
observed CUDA failure or truncation, and successful owned-server shutdown.

## Actual input and transition review

Read the complete artifact-map initial system/user messages. The other two system
messages are byte-identical; read their distinct complete initial user messages.
All contain the original task, truthful episode annotation, root navigation,
empty source/result selection, no account, no earlier action history and no
applicable passing check. No reference patch, target-line answer or researcher
selected group enters these initial inputs. The reference operation sequence is
an offline qualification artifact outside the future actor's initial input.

Read every saved baseline/source/edit/check/submission outcome and inspect the
corresponding actual wire inputs. Each of the five saved stage views exactly
matches a workspace in the native wire-request records, not merely an intended
view or diagnostic counter. In all three cases:

1. The original checker executes and fails on the original candidate. Its actual
   failure and recovery access enter the measured next input.
2. The scripted work_on returns the exact old source range. That body appears in
   working_set.sources before the guarded edit.
3. The edit produces the reference successor and refreshes the selected source.
   The post-edit input remains ineligible for submission; no automatic check ran.
4. A separately requested public check names that actual successor, completes
   and passes. Only then does submission eligibility become true.
5. Submission names the same checked candidate and records a checked submission.

Artifact-map feedback includes the complete observed stale-map state and assertion
trace. Shift feedback names all seven failing cases and shows two complete records
with actual/expected results, stating that five remain for inspection. Receipt
feedback preserves the actual CSV input, names all ten failing cases and shows two
complete records, stating that eight remain. Their full raw streams are captured.
The passing reports do not invent fault-test obligations or carry prior failing
criteria as current after the new passing execution.

The scripted source groups deliberately contain the evaluator-known edit anchor,
not all evidence a model would need to discover or justify the repair. This route
qualifies execution, source eligibility, feedback and current-version closure;
it is not evidence of source discovery, independent diagnosis, autonomous action
selection or a successful Qwen task. Shared operation receipts use origin=model
to identify requested versus automatic operations; the package and records label
these as scripted qualification with zero completions, not observed actor choices.

## Custody and readiness

Each package has 73 sealed output files and 47 records. Independently recomputed
every sealed file's size/hash and every bound source hash against the current
checkout; no differences were found (466, 477 and 481 source bindings respectively).
Each seal is qualified_no_model_inference with completion_requests=0; records
contain no invocation_started event. The normal preparation command also completed
the runner's package verification against the recreated initial candidate and wire
request.

- artifact_map seal: `06052a8ac6a29f6530aec9358ff82156ee0482c704f3d0047d2abf1466986225`
- shift seal: `5bb6b1e74ac73be5ccef9d44b753875597310fd11906b086ecf416fc232650e8`
- receipts seal: `3ec9cf534e49eb0592f2e68a7ea3aca32fbb97f38fec651f6bda2ab171b80844`

The three preparation-001 packages and EXECUTION_MANIFEST-001.json files are ready
for the parent's review and prospective publication. They do not close any new-host
model regression. No live run was launched by this preparation review.
