# Experiment 012 host-path audit

## Audit scope

This audit follows every completed action and every prepared-but-denied request
from exact saved custody. It distinguishes model behavior from host capacity,
call-budget, and terminal decisions. All paths were reviewed after the response
seal and before interpreting hidden correctness.

## Compact trajectory table

| Cell | Condition | What Qwen saw | What Qwen did | What the host did next | Classification |
|---|---|---|---|---|---|
| SOURCE / 173205 | C50 | Full Phase-A chronology, exact Phase B, current candidate, hierarchical P0, 50,176-token slot | Located `policies/current.py`, read `orbit-`, patched `api/name.py`, read both B ledgers, passed check, forked; then read one C ledger | Denied the next Phase-C request before HTTP at physical capacity | Correct B closure; physical C50 stop |
| SOURCE / 173205 | T25 | Fresh Phase B frame, current candidate, P0, Phase-A fork receipt; after reset only the latest exact pair | Produced the same correct B patch and read both ledgers; after two resets repeated policy, target, and ledger acquisition | Allowed fourteen completed calls, then stopped at the frozen phase-call limit; no fifteenth call offered | Model-call-budget exhaustion caused by progress loss |
| SOURCE / 223607 | C50 | Same paired prefix and task under the second seed | Produced the correct B patch, read both ledgers, passed check, forked; reread current policy and one C ledger | Denied the next Phase-C request before HTTP at physical capacity | Correct B closure; physical C50 stop |
| SOURCE / 223607 | T25 | Same T25 frame; reconstructed history exposed only the last retained pair | Produced the correct B patch and both reads; after resets used one literal search, then repeated policy/target/ledger reads | Allowed fourteen completed calls, then stopped at the phase-call limit | Model-call-budget exhaustion caused by progress loss |
| OBS / 173205 | C50 | Full Phase-A chronology and identity directory with candidate-bound `OBS-0002` | Reopened `OBS-0002`, over-confirmed it twice, patched label with `A3::`, read both B ledgers, checked/probed/forked; selected current `OBS-0005`, patched header with `B6::`, read one C ledger | Denied the next Phase-C request before HTTP at physical capacity | Correct B closure and correct C mutation; physical C50 stop |
| OBS / 173205 | T25 | Fresh Phase B frame with `OBS-0002`; after reset only the latest ledger pair plus the persistent identity directory | Correctly reopened `OBS-0002`, patched label with `A3::`, read both B ledgers; after each reset reopened `OBS-0002` and alternated already-complete ledger reads | Three denials triggered reconstruction; the fourth denial stopped before HTTP under the frozen reset limit | Mechanical capacity stop after repeated reacquisition |
| OBS / 223607 | C50 | Same paired observation prefix under second seed | Reopened current `OBS-0002`, patched label, read both B ledgers, checked/probed/forked; selected current `OBS-0005`, patched header, read one C ledger | Denied the next Phase-C request before HTTP at physical capacity | Correct B closure and correct C mutation; physical C50 stop |
| OBS / 223607 | T25 | Same T25 frame and identity-only observation directory | Correctly reopened `OBS-0002`, patched label, read both B ledgers; after resets reopened the same observation and repeated label/ledger reads | Three denials triggered reconstruction; the fourth denial stopped before HTTP | Mechanical capacity stop after repeated reacquisition |

## Shared-prefix path

All four shared Phase-A prefixes completed without a reconstruction or protocol
error. Qwen read both required A ledgers, read and patched
`workflow/progress.py`, passed `prefork`, and called `fork_ready`. Observation
cases additionally called `probe("compatibility")`, creating exact
candidate-bound `OBS-0002` before the branch split.

The source prefixes each used seven HTTP calls. Observation prefixes used nine
and eight. One actor added a harmless `p0_page("records_a")`; all required
paths were otherwise taken directly from the exact phase text. Every prefix
candidate and boundary binding was common to its paired C50/T25 branches.

## T25 reset path

At the first branch boundary, all four full prospective T25 requests were above
25,000 tokens but below the physical slot limit. Each T25 branch therefore
started from the frozen reconstructed frame rather than the full Phase-A
chronology.

Within Phase B, a later exact ledger result made the next request exceed the
25k admission ceiling. The host wrote the full request, endpoint request, and
rendered prompt before denying HTTP. It then:

1. constructed an exact boundary binding over the current candidate, task,
   observation directory, P0 root, active history, and record chain;
2. replaced model-visible history with the last complete action/result pair;
3. retained the same `ToolExecutor`, candidate, required-read gate state,
   observation bodies, call count, and exact external chronology;
4. offered a newly rendered request if the reset allowance remained.

Ten such denials resulted in a fresh request. Two final observation-case
denials did not, because the four-reset allowance had been consumed. The two
source branches never reached a final capacity denial: each exhausted fourteen
actual model calls first.

The host never told Qwen that completed reads were incomplete. It also never
showed Qwen the compact identities of all completed reads. The resulting
asymmetry—host gate remembers, model frame forgets—is the central causal
finding.

## C50 terminal path

All C50 branches preserved append-only history. That allowed Qwen to see its
complete Phase-B progress and close Phase B in every cell. It also caused prompt
growth to 44,401–46,462 server-reported tokens. Each C50 branch then received
one or more Phase-C calls before the next prospective request could not fit the
50,176-token physical slot with the frozen completion/reasoning allowance.

The host denied those four terminal requests before HTTP. No response was
expected or imputed. C50 did not have a reconstruction path by definition.

## Candidate/check path

All mutations were exact candidate/file-bound replacements. No patch was stale
or rejected. All model-visible checks that Qwen actually invoked passed.

After sealing, the final T25 candidates passed their Phase-B checkers even
though T25 had not invoked those checks. Both observation C50 candidates passed
the Phase-C checker after correctly using `OBS-0005` and `B6::`. These facts
show that mutation correctness preceded the terminal resource events; they do
not alter formal phase completion.

## Protocol and runtime path

- strict JSON actions accepted: 129/129;
- completed action results accepted: 129/129;
- duplicate response IDs: zero;
- runtime token-accounting deltas: zero on 129/129 calls;
- check failures: zero;
- stale candidate/file binding errors: zero;
- HTTP/transport/parser failures: zero;
- retries, repairs, rescues: zero;
- server shutdown and port release: verified.

The terminal labels therefore correspond to frozen capacity or call-budget
rules, not accidental host failures.
