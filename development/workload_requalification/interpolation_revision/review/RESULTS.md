# Corrected-report interpolation continuation — results

The ten-request uncoached continuation **did not save a contribution**. It ends
normally at `request_allowance_exhausted`, with the initial candidate byte-for-byte
unchanged and no new tests, documentation, executed check or submission. The report
repairs remain truthful corrections; this run does not demonstrate that they improve
task completion.

Run-002 used the package frozen at c3d6da70. It resumes the exact last committed
C21 checkpoint from interpolation/run-002, with the same task, candidate, account,
source selection, checker definitions and actor/runtime settings. It changes only
the declared report/episode projection and remaining-budget accounting. No reviewer
coaching, injected selection, internal-draft execution, retry or allowance extension
occurred.

## Observed work and cost

| Measure | This continuation |
| --- | ---: |
| Complete replies | 10 of 10 |
| New recorded operations | 12 |
| Source reads / searches / account updates | 3 / 6 / 3 |
| Rejected operations | 0 |
| Artifact edits / new checks / submissions | 0 / 0 / 0 |
| Model-request time | 1,064.343 seconds / 17.739 minutes |
| Task-loop time | 1,117.672 seconds / 18.628 minutes |
| Input tokens | 186,097 |
| Generated tokens | 11,226 |
| Peak input | 23,690 tokens |
| Peak input plus generation | 24,315 tokens |
| Minimum sampled free GPU memory | 265 MiB |

All ten replies finish normally with executable final content. No physical context
exhaustion, allocation failure or omitted selected source occurs on the recorded
path. Eleven nonterminal operation receipts are represented in the following model
input; the final search receipt has no subsequent call. Receipt presence alone is
not the delivery claim: the direct review also checks the actual returned fields
and delivered source.

The original interrupted attempt contributed 21 completed replies, 34 operations,
32.179 known model-request minutes and 22,731 generated tokens. Its C22 was sent
without a preserved response or complete cost. Across the two attempts, 32 requests
were dispatched, 31 completed responses survive, and 46 operations were recorded.
The **known** model-request cost is 49.918 minutes and 33,957 generated tokens.
The unknown original C22 remains excluded, not silently assigned zero cost. Fifty
operations remain unused when the original request allowance closes.

## What the actual inputs and outputs establish

The complete missing-operation grouping is visible throughout. Qwen enumerates
the required transports, raw bypass and successful resolution correctly in the
first response; later responses retain those distinctions. It does not reproduce
the original invented HIGHEST/DEFAULT decomposition as an extra requirement.
That is an observed interpretation, not an isolated causal effect: the original
run sometimes also resolved the grouping and the inherited account already held
part of it.

The contribution remains in source acquisition. Qwen repeatedly seeks test class
structure, existing helpers and an insertion location. It follows one real helper
location, obtains the actual helper body, and later finds another helper through
search. Several acquisitions therefore supply useful information. They never turn
into new tests or documentation within the allowed journey.

The preserved account carries task and acquisition plans, then one newly inspected
helper finding. It is not used in a saved edit. One response announces a search but
emits only an account update, which the host executes as precisely that update.
Neither account acceptance nor accurate task restatement establishes productive
continuity.

A regex-shaped query reaches the literal-only search tool in C09. The resulting
zero matches are truthful for the actual query. C10 recognizes the mismatch and
tries a literal name; the unsuccessful regex search is an executed interaction
cost, but not a persistent belief that relevant classes do not exist. Earlier
source-location results also disappear from immediate feedback after intervening
operations, while recent rows preserve their queries. These are concrete interface
and navigation issues to assess, without blaming false storage or missed delivery.

The source/selection/feedback core worked on this path. The combined system still
failed to move from its acquisition plan into an actual contribution. This run
does not qualify guarded edits, path-triggered checks, post-failure correction,
selection replacement, durable proposals or checked submission: none occurred.

## Verification and limits

Exact replay verifies 410 source identities, 207 custody records, thirteen native
inputs, all ten complete replies and every recorded effect without model inference
or checker execution. It preserves the difference between 34 inherited contribution
operations and twelve new ones, plus 55 actions from earlier completed work. All 55
current-source extents displayed across the ten calls match the designated candidate.
Normal runtime shutdown and the dedicated port being free are recorded and verified.

See `TRANSCRIPT_REVIEW.md` for every complete response, `HOST_ARTIFACT_AUDIT.md`
for boundary and artifact findings, `VERIFICATION.json` for exact replay,
`ASSESSMENT.json` for per-call measurements and `CUMULATIVE_COST.json` for inherited
cost accounting. `saved-contribution.patch` is empty because no file changed.

This is one development continuation after an interrupted and previously exposed
prefix. It supplies no success rate, controlled performance comparison or fresh
whole-backport result. The old failed check remains applicable because the candidate
and checker are unchanged; it is inherited evidence, not a newly executed check.
The unsuccessful outcome and consumed allowance stay closed.
