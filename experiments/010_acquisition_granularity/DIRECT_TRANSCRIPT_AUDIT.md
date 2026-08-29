# Experiment 010 direct transcript audit

## Review method

This is a condition-aware post-seal audit of every saved model input and output:
61 coding requests, rendered prompts, raw endpoint responses, private reasoning
records, final action objects, tool results, candidate transitions, and host
decisions. It is not a blinded review.

The actor was Qwen3.8-27B-AD-IQ2_S with low private reasoning capped at 512
tokens. Reasoning was exact-custodied separately and omitted from subsequent
history. Both conditions used temperature 0.7, top-p 0.8, top-k 20, presence
penalty 1.5, one attempt, and no feedback between cells.

## Per-trajectory audit

| Cell | What Qwen saw | What Qwen did | What the host did next | Interpretation |
|---|---|---|---|---|
| Alpha / 173205 / L0 | P0 named two 7.1-7.3KB ledgers and a two-line target; read accepted actor-selected count | Chose 500 lines for each ledger, then read target once, patched 0→2, checked, closed | Each 500-line request returned all 198 exact lines with `complete=true`; patch/check/fork all accepted | Qwen used the available maximum conservatively enough to avoid fragmentation; 7 calls |
| Alpha / 173205 / L1 | Same world, but read promised the largest exact bounded page | Read each ledger once, read target, then reread the identical target before patching, checking, and closing | Both ledger reads returned all 198 lines; both target reads returned the same two current lines | L1 removed page choice but did not prevent no-new-information confirmation; bounded reasoning stalled while asking what “completed” meant; 8 calls |
| Alpha / 223607 / L1 | Same L1 contract under the second seed | Read each ledger and target once, patched, checked, closed | All exact reads complete in one call | Direct minimal path; 7 calls |
| Alpha / 223607 / L0 | Same L0 contract under the second seed | Requested 50 lines of the first ledger, observed continuation 51, deliberately estimated remaining length and requested 200; read second ledger with 200, target with 10, then closed | Host returned exact 1-50 and 51-198 pages, then complete second ledger | Qwen adapted correctly after one conservative page, but paid one extra transfer; 8 calls |
| Beta / 173205 / L1 | Fresh lexical sibling with two 7.3KB ledgers | Read each ledger and target once, patched, checked, closed | All exact reads complete in one call | Direct minimal path; 7 calls |
| Beta / 173205 / L0 | Same Beta task with actor-selected count | Chose 100+100 for first ledger, then 200 for the second after learning the 198-line extent; read target, patched, checked, closed | Exact continuation made the first split non-guessing; second ledger completed in one call | Qwen learned from the first result but still paid one fragmentation call; 8 calls |
| Beta / 223607 / L0 | Same Beta task under second seed | Chose 100+100 for both ledgers, then target, patch, check, close | Four ledger pages were exact and complete | Persistent conservative physical policy consumed two avoidable calls but stayed within the ten-call budget; 9 calls |
| Beta / 223607 / L1 | Same world with maximal bounded pages | Read both ledgers and target once, patched, checked, closed | Both ledgers returned all 198 lines | L1 removed both conservative splits; 7 calls |

## What the reasoning reveals

L0 did not blindly use one fixed page size. It reasoned from P0 byte size,
estimated average line length, watched `next_start_line`, and sometimes enlarged
the next request from 50 to 200 or from 100 to 200. This shows physical paging
is a real actor policy decision, not a parser artifact. It also shows the actor
can adapt, but does so inconsistently across seeds and lexical siblings.

L1 was immediately legible. In all four cells Qwen selected the same correct
files and start lines, understood `complete=true`, and never invented a
continuation. Removing `line_count` did not confuse source acquisition.

The sole L1 regression was not caused by page size. In Alpha seed 173205, Qwen
had already received the unchanged two-line target. Its next private reasoning
reconsidered the meaning of “completed ledger files,” ran to the bounded
reasoning limit mid-thought, and emitted the same exact target read again. On
the following invocation it recognized both ledgers as complete and patched.
This is the same failure class identified separately in Experiment 009:
confirmation policy, not evidence location or transfer granularity.

All eight actors correctly distinguished P0 orientation from exact source.
They read the target before mutation, used current candidate/file hashes,
patched only after both required ledgers were complete, checked the successor,
and closed. No private rationale contradicted the emitted action in a way that
changed candidate quality.

## Paired economics

L1 used fewer calls in three of four pairs:

| Pair | L1−L0 calls | L1−L0 prompt tokens | L1−L0 elapsed |
|---|---:|---:|---:|
| Alpha / 173205 | +1 | +10,627 | +57.1 s |
| Alpha / 223607 | -1 | -2,986 | -18.8 s |
| Beta / 173205 | -1 | -4,202 | -29.9 s |
| Beta / 223607 | -2 | -13,032 | -46.3 s |

Aggregate L1 removed four ledger-page calls, but the duplicate target read
returned one call. Net effects were 29 versus 32 total calls, 202,821 versus
212,414 prompt tokens, and 914.3 versus 952.1 seconds. Hidden quality and
closure were 4/4 in both conditions.

## Host-path review

Every emitted action produced an accepted result. No next action was withheld,
no request was capacity-denied, and no call budget was exhausted. There were no
malformed actions, stale bindings, checker errors, HTTP errors, retries, or
operator interventions. The inherited terminal label is reporting-only; the
last visible host response in every cell was accepted `fork_ready=true`.

## Falsifiable hypotheses carried forward

1. In a fresh recurrent path where complete acquisition competes with a hard
   action/context budget, L1 will prevent page-fragmentation noncompletion.
2. L1 will not prevent duplicate confirmation of an already-visible exact
   current range; that failure should be tracked independently.
3. When no duplicate confirmation occurs, L1 should save at least one action
   and several thousand cumulative prompt tokens whenever L0 initially chooses
   fewer lines than the exact page can hold.
4. If a fresh recurrent L1 path still fails after all required files arrive in
   one page, the next earned mechanism concerns confirmation/closure policy,
   not richer metadata.
5. The setup-only `begin` invocation is common overhead and may be removable in
   a later controller simplification, but it is not part of this comparison.
