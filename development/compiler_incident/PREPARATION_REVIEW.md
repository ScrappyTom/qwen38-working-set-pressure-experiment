# Compiler incident task: preparation review

The new task qualifies for a **repair-and-incident-report pressure experiment**.
All six short scripted routes cross the proposed 16,000-token input limit while
remaining below the 23,808-token resident ceiling. An actual externalized
continuation retrieves missing evidence and reaches checked submission. Zero
Qwen completion requests were sent. The shared host and current interface remain
unchanged.

The qualification is narrower than independent discovery of the repair. The
optimizer fault can be identified from source; the historical comparison is the
part that requires incident evidence. This is a useful next pressure task, not
a claim that we have forced or demonstrated a changing hypothesis, an incorrect
repair, or model recovery. Those distinctions are explicit in the frozen
[specification](SPEC.md).

## What the actor has to do

Two captured optimized calculation builds have different observed symptoms: an
inverse-normal call raises `ValueError`, and a Weibull call returns a complex
number. The original calls returned real numbers. The actor receives the task,
ordinary repository navigation, and three readable capture identities. It can
retrieve the original and either emitted module using the existing exact tool.

The task asks for a bounded optimizer repair and an incident report identifying
the functions actually changed in each build and the first changed expression.
That report is a normal task artifact, edited using existing guarded patches.
No diagnosis, acquisition order, complete reading list or obligation to fail a
check is supplied. The report's format and the supported compiler contract are
available in the candidate README.

The calculations are two extracted CPython v3.12.10 functions, with their exact
[provenance and changes](donor/PROVENANCE.json) and upstream license retained.
The calculation source is 3,789 bytes, without added data. Captures are full
default Python AST dumps, excluding location attributes, obtained by executing
the authored optimizer. Their stored sizes are 9,228, 9,168 and 9,180 bytes.
The candidate is six text files totaling 3,665 bytes. This is an authored compiler
defect using real calculation code, not a reported CPython or production defect.

The information requirement is concrete. Original source alone does not identify
what each historical build emitted. Either build's selection can differ without
changing the other two records or its reported symptom. Also, both lossy emitted
trees can remain identical under a different original unary expression, so their
overlap does not uniquely reconstruct the original syntax. These evaluator-side
counterfactuals qualify report ambiguity. They do not make the repair itself
incident-dependent or prove that a future model used the captures.

Pressure here comes from full captured trees and retained exact history, despite
the small editable compiler. This qualifies that concrete information surface
under the current atomic observation-access contract. It does not show that full
AST records are the best possible interface or that another granularity would
have the same cost. No alternate retrieval tool or record representation is being
smuggled into this comparison.

## Actual offline results

| Scripted route | Actions | Peak native input | First input above 16,000 |
|---|---:|---:|---:|
| Minimum with report schema already known | 9 | 18,934 | Before action 6 |
| Evidence first | 10 | 19,870 | Before action 5 |
| Source first, including useful navigation | 13 | 21,582 | Before action 10 |
| Incremental report | 11 | 20,812 | Before action 7 |
| Public check first | 11 | 20,703 | Before action 9 |
| Partial repair, failed check, correction | 12 | 21,329 | Before action 5 |

These are actual tool executions with known solutions, not Qwen trajectories.
The optimistic minimum omits the README acquisition; it is a conservative capacity
probe rather than additional schema knowledge supplied to the actor. The other
orders include the task's existing contract/schema acquisition. No filler or
unnecessary file-reading requirement produces the boundary.

The largest input leaves 34,994 physical tokens for generation, above the existing
32,768 planning reserve. The partial-repair path has 23 actions remaining after
its failed check and completes in 12 of 32. That is measured action opportunity
plus admission on this particular continuation, not a promise that any sequence
of later choices will fit. The proposed seeds remain 49979687 and 67867967.

All 26 public contract cases execute in each acceptance probe. Results separate
the application and artifact obligations:

| Candidate variant | Passing cases |
|---|---:|
| Original compiler and empty report | 13/26 |
| Correct repair, empty report | 25/26 |
| Correct report, original compiler | 14/26 |
| Incomplete sign-handling repair, correct report | 24/26 |
| Optimization disabled, correct report | 19/26 |
| Correct repair, wrong historical scope | 25/26 |
| Correct repair and correct report | 26/26 |

The checks exercise explicit behavioral expectations for values, types, signed
zero, custom unary operations, exceptions, side effects, literal folding, scope,
nonselected source, independent AST ownership and async functions. They do not
grade by agreement with the donor implementation. A separate replay of the actual
calculation module confirms that the repaired compiler preserves both original
trees and restores both recorded calls. That is additional application checking,
not another experimental score. Report validation accepts equivalent spacing and
parentheses, and either build-row order; it does not print the expected findings.

## The boundary and exact recovery were exercised

On the incremental-report route, actions 1–6 read the contract and report, acquire
the original and A, record A's comparison, and acquire B. The next full input grows
from 13,821 to **17,753** tokens. An exact prefix copy preserves the candidate,
history, recovery maps and execution/check state before changing residency.

Externalizing the oldest three event payloads gives a **13,760-token** input.
The original capture's body is absent, while its address and readable result
signal remain. A's already-written comparison remains in the actual report and
resident patch text. The qualification then performs an explicit exact retrieval
of the original. Its 9,441-byte wrapper returns all 9,228 original bytes unchanged.
After admission at **14,211 tokens**, the next prepared input contains the recovered
original, B's exact tree and A's partial report. This was directly inspected in
the saved request and patch/result records, not inferred from counters alone.

The branch completes both report and repair, consumes the current check result,
and submits the same final candidate as its resident counterpart. It takes
**12 actions**, including that one additional retrieval. Its largest admitted
continuation input is **15,817**. Larger admission trials are saved as unsent
inputs. This retrieval is an offline scripted action, not a model-selected action
or a new host rule about what evidence matters.

Separately, every original observation, saved result and patch payload was
reopened from an exactly replayed pre-submit state: **13 exact bodies**, all
within the 22,000-byte wrapper limit, with unchanged execution state and canonical
identity. This forced plumbing check does not count as another natural boundary.
No model input was constructed after submission. A separate clone test preserves
a current passing check and verifies that editing the clone leaves its parent
unchanged.

## Custody, checks and preparation corrections

[Verification](VERIFICATION.json) checks **403 public artifacts, 68 source hashes,
158 custody records and 79 saved native inputs**. It independently replays all
66 resident actions and the six post-prefix external actions, including recovery,
and checks every action against the saved output grammar. Template bytes and
recorded token arrays agree. This is not an independent tokenizer rerun.

**19 selected tests passed**: 13 for this task and six for the reused incident
preparation/recovery helpers. This is not a full-suite run. The owned native
runtime closed cleanly with the dedicated port released; sampled free GPU memory
reached 501 MiB. No inference occurred, so this does not qualify hard-task
generation or replace the accepted advisory memory policy. The request path uses
only rendering and tokenization. The runtime's ordinary log is not being treated
as a complete HTTP request audit.

The [preliminary screen](PRELIMINARY_SCREEN.md) remains unchanged at commit
`ef5a35306d23209adefa39e5adf40c83328579b4`. Its placeholder checker was never called.
Its subprocess wrote Python caches after candidate construction; their exact
bytes are preserved separately. The qualified builder copies only the six text
files into a fresh temporary checkout and disables bytecode.

Before the sealed preparation, ordinary development checks exposed two mistaken
uses of the Candidate API (`read_text` does not exist; `file_map` is a property),
and importing `asyncio` failed with WinError 10106 in the restricted checker
environment. The fixture now checks its non-suspending coroutine directly, and
every negative acceptance probe must show that all contract cases completed.
One initial synthetic-count test did not remove the original at the intended
point; its mock was corrected to exercise that branch. The actual native counts
above were measured afterward. These corrections changed preparation/checking
code, not the shared host, actor policy or any consumed model evidence.

Seal aggregate: `b8e8145806c13609b0c191b24e1d202ddd34ac614fd955418cac8838be7734a2`.

## Recommendation and remaining limits

Retain this candidate and prepare the separately bound execution runner for the
proposed 16,000-versus-23,808 comparison. The task now supplies a concrete pressure
opportunity, useful exact recovery, and a checked contribution beyond a single
source edit. No additional interface redesign or tiny wording study is earned.

The scope is **incident reporting and repair across pressure**. It does not yet
establish independent discovery of an incident-dependent repair, a reversal after
contradictory execution evidence, or failed-repair recovery by Qwen. The source
repair can be obvious; the partial report can preserve findings. Neither fact
should be concealed to make an external-memory claim stronger.

Finite scripted routes do not prove that every successful actor path will fork.
Prior knowledge, correct inference or guesses tested through public feedback may
yield a shorter passing artifact. Preserve any such actual trajectory without
manufacturing pressure. Inspect all evidence copies and judge what Qwen actually
uses. Long deliberation alone still does not earn a consultation or interface
change; a consequential misunderstanding does earn a separate neutral dialogue.

The current task-selection authorization is fulfilled by this offline package.
Live requests still need the concrete execution safeguards and the separate owner
decision required by [SPEC.md](SPEC.md). The accepted GPU-margin decision is not
being reopened. No model requests or automatic successor have been activated.
