# Artifact-map repair regression: checked completion

The uncoached run frozen at `3107f3cf` completes the original artifact-map task on
the revised host. Qwen selects its own sources, saves the one-line map rebuild,
requests the unchanged public checker on the actual successor, receives its pass,
and submits that same candidate. Independent source review supports the repair.
No researcher supplied a diagnosis, selected source group or operation during the
run. The original task, candidate and checker were reused as a development
regression; this is not a fresh capability task or a controlled speed comparison.

| Measure | Observed result |
| --- | --- |
| Model requests | 20 of 24, all complete |
| Recorded operations | 30 of 72; none inherited |
| Operations | 11 tree, 2 outline, 4 read, 10 account, 1 patch, 1 explicit check, 1 submit |
| Model-request time | 1,201.283 seconds / 20.021 minutes |
| Task-loop time | 1,304.640 seconds / 21.744 minutes |
| Cumulative input / generated tokens | 150,805 / 16,120 |
| Peak input / input plus generation | 14,687 / 18,876 |
| Input ceiling / physical context | 23,808 / 56,576 |
| Minimum sampled free GPU memory | 266 MiB; original reference remains advisory |
| Rejected actions / failed checks | 0 / 0 |
| Immediate nonterminal receipts represented | 29 of 29 |
| Saved artifact | One source line changed; other 24 files byte-identical |
| Runtime closure | Owned server shutdown and dedicated port release verified |

The repair replaces `new_map = address_map` with
`new_map = build_address_map(new_artifact)` in `patching.py`. It aligns returned
unit ranges, hashes and version identity with the actual edited artifact while
leaving stale-preview and stale-reopen rejection unchanged. The original checker
completes all eight assertions; its full 695-byte stdout and empty stderr are
preserved. There is no additional evaluator check execution in this review.

The saved successor is
`23b5c17999963faf7453c68a6b537ae6c447555f77eb0a835bfa659ad47e89aa`.
Its explicit public check uses definition
`dfabb33ffefc5b9649332ed87c7d6dc16b7b345380fe96bc7bfa7c78220bb911`.
C20 consumes that actual applicable pass before submitting.

Success does not conceal two host presentation costs. Discovered directory pages
and outline locations disappear after the next operation even with substantial
room available. C16 explicitly seeks a prior tree's absent result. The post-edit
input also shows updated source and an edit receipt, but neither the old fragment
nor the exact diff; C19 repeatedly tries to reconstruct what changed. Exact
archives preserve both types of information, but ordinary presentation does not.
These omissions are verified in actual inputs. Their individual causal effect on
cost and the benefit of a revised view remain unmeasured. C09 is a counterexample
to a solely missing-information explanation: its complete outline is visible when
it chooses another directory listing.

All twenty complete transcripts were directly reviewed. Exact replay verifies 466
source identities, 458 custody records, 31 distinct native inputs, all twenty
replies, intermediate/final states, and the saved observation without executing a
checker or requesting inference/tokenization. Seventeen displayed current-source
extents match exact candidate bytes. Review helpers completed on their first run.

The regression passes this task's contribution boundary. No capacity recovery,
group replacement, failed-repair correction or sustained pressure is exercised.
Ten account updates do not by themselves demonstrate account benefit. Retain the
checked repair and these adverse presentation findings; prospective host changes
must preserve this result and receive separate qualification.
