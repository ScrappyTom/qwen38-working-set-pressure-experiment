# Server-budget development finding

## Disposition

The development-only check passes its runtime-control purpose and identifies a
meaningful source-acquisition signal worth one small fresh replication.

The check used the already-exposed `E4-SOURCE` fixture and a mechanically
scripted exact prefix. It is not a fresh measured result and is not an authentic
second pressure event. Its purpose was to verify the server-side reasoning cap
and test the missing source R0/R1 transition without spending another bank.

## Runtime-control result

The shared llama-server was launched with:

```text
--reasoning auto
--reasoning-budget 512
--reasoning-format deepseek
--no-reasoning-preserve
```

R0 emitted zero private-reasoning artifacts. R1 emitted one private-reasoning
artifact for every call. Exact pinned-tokenizer counts were:

```text
221, 217, 313, 478, 511, 511, 220, 98
```

The maximum was 511. The server-side setting therefore supplied the hard bound
that the prior per-request-only configuration did not.

## Direct transcript result

Every coding request, assistant action, result, and R1 private reasoning trace
was inspected directly.

R0 took this path:

```text
read release/key.py lines 1-5
read release/key.py lines 1-10          # redundant
read policy/namespace.py lines 1-240    # complete large file
read release/render.py
patch using active_namespace()
check public
submit
```

R1 took this path:

```text
read release/key.py
read policy/namespace.py at P0 symbol range 230-232
read policy/namespace.py lines 1-30 to resolve ACTIVE_NAMESPACE
read release/render.py
read release/key.py again               # redundant
patch using imported ACTIVE_NAMESPACE
check public
submit
```

R1's reasoning explicitly identified the target, governing namespace, P0
symbol range, normalization constraints, render dependency, patch, check, and
submit. It followed that plan. The traces remained repetitive: calls 5 and 6
reconstructed the same state and reached the cap, and call 5 caused an
unnecessary second target read. The cap bounded this repetition without
preventing a valid strict action.

Both terminal candidates passed public and hidden grading. R0 used the current
`active_namespace()` function; R1 imported `ACTIVE_NAMESPACE`. Neither was
byte-identical to the task author's simple hard-coded known-good patch, but both
preserved the required behavior.

## Economics

| Measure | R0 | R1 hard-capped | Difference |
|---|---:|---:|---:|
| Hidden pass | yes | yes | tie |
| Submitted | yes | yes | tie |
| Calls | 7 | 8 | R1 +1 |
| Exact read content | 13,079 bytes | 2,007 bytes | R1 -84.7% |
| Cumulative prompt tokens | 59,223 | 31,084 | R1 -47.5% |
| Maximum prompt tokens | 13,487 | 5,373 | R1 -60.2% |
| Completion tokens | 498 | 3,040 | R1 +2,542 |
| Prompt + completion tokens | 59,721 | 34,124 | R1 -42.9% |
| Endpoint time | 151.490 s | 219.297 s | R1 +67.807 s |

The result is not simply “thinking costs more.” Private reasoning cost more
completion tokens and wall time, but its more targeted exact acquisition saved
far more prompt tokens in this large-file geometry. The total token economy was
better even with one extra call.

## Interpretation and next decision

The prior observation pair showed no outcome or token-economy advantage from
reasoning. This source case shows a plausible context-management advantage:
bounded reasoning used readable P0 ranges to avoid pulling a complete large file
into append-only history.

Because the fixture was already exposed and the fork was scripted, this is only
development evidence. It is nevertheless a directly observed, feature-specific
need satisfying the project's earned-feature rule.

The next justified study is a minimal fresh constructed-fork replication:

- two fresh source-reacquisition geometries;
- same exact actor, P0, pointer, tools, fork state, seed, and 25k envelope within
  each pair;
- R0 reasoning off versus R1 server-capped at 512;
- one seed per geometry with branch order alternated;
- no live actor prefix, because the treatment begins at reconstruction;
- quality first, then exact read bytes, prompt tokens, calls, latency, and
  closure;
- no semantic summaries or host-selected relevant facts.

If R1 again preserves quality while materially reducing exact acquisition and
prompt occupancy, bounded reasoning becomes a candidate part of the managed
25k controller. If it only adds output/latency cost, keep the main program
reasoning off.

