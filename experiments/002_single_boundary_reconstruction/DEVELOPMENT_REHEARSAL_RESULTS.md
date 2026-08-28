# Development live-rehearsal results

## Disposition

The Experiment 002 state machine is qualified for measured freeze preparation.
This is development evidence, not a measured result. No fresh measured fixture
was exposed.

One exact shared prefix reached the authenticated fork after 14 completion
calls. The matched continuations then diverged:

| condition | HTTP calls after fork | terminal state | hidden quality | maximum prompt |
|---|---:|---|---|---:|
| C50 append-only | 6 | checked and submitted | pass | 35,003 tokens |
| T25 reconstructed | 3 | fourth request denied before HTTP | unchanged continuation candidate | 31,537 prospective prompt tokens |

The T25 total was 34,549 tokens after the frozen 512-token runtime allowance
and 2,500-token output allowance, above its 25,000-token active envelope.

## What the actor actually saw

The first T25 request contained the exact original two-phase task, current
candidate and P0 directory, `stage: continuation`, the exact accepted
`fork_ready` action/result, and a complete directory of three reopenable
prefix observations. It explicitly said older chronology was absent and
should be reacquired only when needed. It did not contain a semantic summary,
host-selected relevant source, or evaluator truth.

The full C50 request retained all 14 prefix action/result pairs, including the
three exact large-file reads, the readiness repair, the successful prefork
check, and the accepted fork boundary.

## Direct transcript audit

The shared-prefix actor initially behaved coherently but inefficiently. It
read the three required audit files and readiness source, learned from a
failed prefork check that readiness was still wrong, then attempted
`fork_ready` four times before making the required patch. It finally repaired
`audited_count()`, passed `prefork`, and crossed the exact boundary. The
prefix grew from 888 to 32,381 server-reported prompt tokens.

C50 used the retained chronology as working memory. It immediately read the
two small Phase B files and only the three governing lines at the end of the
already-audited policy file. It then imported `release_prefix`, repaired
`release_tag`, passed the public check, and submitted. The final candidate is
not byte-identical to the task-author known-good candidate, but it passed the
independently sealed hidden grader and preserves the same governing behavior.

T25 did not use the accepted boundary as sufficient evidence that Phase A was
complete. It restarted the three exact large-file reads in original task
order: all of `audit/alpha.py`, all of `audit/bravo.py`, then all of
`policy/channel.py`. It did not reopen a prior observation, inspect the small
Phase B targets, or mutate. The first three server prompts were 2,164, 11,944,
and 21,706 tokens. Once those exact read results entered the fresh append-only
branch history, its next request no longer fit the 25k envelope.

This is not evidence that exact reconstruction is impossible. It is evidence
that the present reasoning-off actor does not infer a useful working set from
mechanical continuity alone in this development trajectory. The full task
still begins with Phase A instructions; after reset, the actor appears to
follow them from the beginning despite `stage: continuation` and the accepted
fork receipt. Exact custody and P0 made the old source available, but did not
teach the actor which old information did not need to be reloaded.

## Apparatus findings and treatment discipline

Four earlier development lifecycles found path, grammar, tokenizer, and
multi-page-read defects before measured exposure. The fifth found that an
expected capacity denial was incorrectly classified as a global adapter
failure. Commit `5825c2f` fixes only that classification: it preserves the
prospective denied request, records zero HTTP calls, seals the branch as
`capacity_stopped_before_http`, and allows the matched control to continue.

The C50 follow-up replayed the exact preserved prefix rather than regenerating
it or repeating the 14 model calls. The T25 behavior was not repaired, retried,
or removed. The measured treatment is therefore not changed in response to
this result.

## Measured-readiness decision

The rehearsal establishes all required execution paths:

- authentic shared chronology above the 25k boundary;
- an exact fork from one preserved model trajectory;
- C50 live continuation through read, patch, check, and submit;
- T25 live reconstruction and exact fail-closed capacity exhaustion;
- matched execution after a branch-level model/capacity outcome;
- exact request/response custody, server shutdown, replay, and hidden grading.

The fresh two-family measured bank remains untouched. It should now be run as
frozen. A measured T25 restart is an experimental result, not a reason for host
rescue or a post-hoc semantic summary.
