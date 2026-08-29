# Experiment 009 direct transcript audit

## Scope and method

- reviewer: Codex, primary project agent;
- review mode: condition-aware post-seal direct audit;
- actor: Qwen3.8-27B AD-IQ2_S;
- runtime: llama.cpp b10434, full GPU offload;
- reasoning: enabled, `low`, server-bounded to 512 private tokens per call,
  separately custodied and omitted from subsequent active history;
- sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0.0,
  presence penalty 1.5, repeat penalty 1.0;
- response allowance: 2,500 tokens;
- conditions: C50 append-only under the 50,176-token physical slot and T25
  exact reconstruction under a 25,000-token total envelope;
- seeds: 173205 and 223607.

All 112 completed calls were directly reviewed. The review covered the exact
coding request, what world and history were visible, the rendered prompt, the
private reasoning, final JSON action, exact tool result, candidate/check
binding, and next host transition. `TRANSCRIPT_INDEX.json` binds every reviewed
call to its artifact hashes.

## What Qwen saw after each reset

T25 did not receive a semantic summary or a host-selected relevant fact. Its
fresh request contained:

- the exact original user-authored task;
- the exact active user-authored phase and completed-phase list;
- the exact current candidate ID;
- current candidate-derived P0 paths, symbols, signatures, line ranges, and
  file sizes;
- the latest accepted boundary action/result;
- the complete identity-only observation directory with exact candidate IDs,
  hashes, and reopen handles;
- current tool and invocation limits;
- explicit notice that older exact chronology was externally custodied but
  absent.

Observation bodies were not previewed. Qwen had to choose a handle and reopen
the exact result before relying on it.

## Shared prefixes

All four prefixes completed Phase A correctly. Each actor:

```text
begin
read all three required archive custody files completely
read stage/ready.py
patch completed_groups() to return len(PHASE_A_GROUPS)
check prefork: pass
probe beacon or pulse: obtain the Phase-A candidate-bound marker
fork_ready
```

Cells 02–04 used nine calls. Cell 01 used ten because it read
`beacon/label.py` before `fork_ready`, noticed the stage requirement in the
next reasoning turn, and then issued the boundary action. That extra read was
preserved in both branch histories.

The private reasoning consistently identified Phase A, tracked completed
requirements, and produced exact candidate/file-bound patches. No prefix
reactivated Phase B or C early.

## Cell 01: Alpha, seed 173205

### C50 Phase B

Qwen retained the complete Phase-A chronology. It acted:

```text
reopen OBS-0002                -> C3%%, bound to Phase-A candidate
patch beacon/label.py          -> prepend C3%%
check public                   -> pass
probe beacon                   -> N9%%, bound to Phase-B candidate
read bridge/amber.py completely
read bridge/brass.py completely
```

Because the prior prefix had already exposed the two-line label source, C50
patched without rereading it. The next prospective request was denied before
HTTP at the physical context limit. Qwen was never offered the required
`fork_ready`, so this branch did not enter Phase C.

### T25 Phase B

The first reconstructed request exposed the Phase-B pointer, current P0, the
Phase-A candidate, and `OBS-0002`. Qwen correctly reopened `OBS-0002` and
reasoned that `C3%%` was the governing marker. It then read the two-line label
twice before patching:

```text
reopen OBS-0002                -> C3%%
read beacon/label.py
read beacon/label.py           -> redundant
patch                          -> correct C3%% implementation
check public                   -> pass
probe beacon                   -> current N9%% observation
read amber completely
read brass completely
```

The second read was not caused by missing information. In its private
reasoning, Qwen explicitly quoted the source already present in history,
derived the exact patch, then ended mid-deliberation and emitted another read.
The ninth prospective request (`fork_ready`) exceeded the 25k total envelope
and was denied before HTTP.

Interpretation: observation selection and mutation were correct; local
repetition consumed the one-call/context margin needed for recurrence.

## Cell 02: Beta, seed 173205

### T25 Phase B and authentic boundary 2

This branch used the intended eight-action path:

```text
reopen OBS-0002                -> L6!!, Phase-A candidate
read pulse/label.py
patch                          -> prepend L6!!
check public                   -> pass
probe pulse                    -> P4!!, Phase-B candidate
read bridge/cobalt.py completely
read bridge/indigo.py completely
fork_ready
```

The subsequent Phase-C append-only request was mechanically denied under 25k,
creating the second authentic reconstruction.

### T25 Phase C

The fresh request displayed six observation identities. The older probe was:

```text
OBS-0002 -> candidate 80d6... -> pulse
```

The current probe was:

```text
OBS-0005 -> candidate e394... -> pulse
```

The request's current candidate was `e394...`. Qwen's private reasoning
explicitly compared those bindings, called `OBS-0002` stale, selected
`OBS-0005`, and acted:

```text
reopen OBS-0005                -> exact pulse_marker=P4!!
read pulse/header.py
patch                          -> "P4!!" + name.strip().casefold()
check public                   -> pass
submit                         -> exact checked candidate
```

The submitted candidate exactly matched the known-good identity and passed the
post-seal hidden grader.

### C50

C50 followed the same semantically correct Phase-B path through the two bridge
reads. Its prospective `fork_ready` request exceeded the physical 50,176-token
slot. It never received Phase C.

Interpretation: this is a clean two-boundary observation-continuity success for
T25 and a mechanical capacity failure for append-only C50.

## Cell 03: Alpha, seed 223607

### C50 Phase B

C50 reopened `C3%%`, read and patched the label correctly, passed, probed
current `N9%%`, and read both bridge files in one request each. The next
prospective `fork_ready` exceeded the physical context and was denied.

### T25 Phase B

Qwen again understood every semantic requirement:

```text
reopen OBS-0002                -> C3%%
read beacon/label.py
patch                          -> correct
check public                   -> pass
probe beacon                   -> current N9%%
```

P0 showed each bridge file's terminal function at lines 197–198, the response
schema permitted up to 500 lines, and the private reasoning stated that each
file had 198 lines and must be read completely. Nevertheless, Qwen chose
50-line pages:

```text
amber 1-50
amber 51-100
amber 101-150
amber 151-198
brass 1-50
brass 51-100
brass 101-150
```

The twelve-action budget then ended before the final brass page and
`fork_ready`. The reasoning accurately tracked the pages but did not recognize
the budget failure until it was unavoidable.

Interpretation: this is not unclear semantic behavior and does not warrant a
thinking-on rerun. Reasoning was already enabled. The actor made a conservative
page-size choice despite possessing the exact file extent and legal larger
page size. The failure belongs to information/action economics.

## Cell 04: Beta, seed 223607

### T25 Phase B and authentic boundary 2

Qwen used the efficient eight-action path, reopened `L6!!`, made the exact
Phase-B repair, passed, captured current `P4!!`, read both bridge files in
single 200-line requests, and issued `fork_ready`. The exact next request
crossed 25k and triggered the second reconstruction.

### T25 Phase C

The actor again saw the stale `OBS-0002` and current `OBS-0005` candidate
bindings and immediately reopened `OBS-0005`. It then performed:

```text
reopen OBS-0005                -> exact P4!!
read pulse/header.py
read pulse/label.py            -> unnecessary confirmation
read pulse/header.py           -> redundant confirmation
patch                          -> exact P4!! repair
check public                   -> pass
submit
```

Its reasoning shows why. It had already derived the correct patch after the
first header read, then decided to inspect the Phase-B analogue and later to
reconfirm the unchanged target "to be safe." The extra reads cost two calls but
did not threaten the eight-call Phase-C budget. The final candidate passed the
hidden grader.

### C50

C50 completed the correct Phase-B work and both one-page bridge reads, then
hit the physical context ceiling before `fork_ready`.

Interpretation: semantic observation validity was robust across the second
seed. Local acquisition remained more cautious than necessary.

## Compact causal table

| path | what Qwen saw | what Qwen did | what host did next | interpretation |
|---|---|---|---|---|
| Alpha/173205 T25 B | exact Phase-B pointer, current Phase-A observation ID, P0 extents | selected correct observation and patch, but reread target | denied ninth prospective request at 25k | correct semantics, repetition defeated closure |
| Beta/173205 T25 C | stale and current probe identities with candidate bindings | selected current `OBS-0005`, reopened `P4!!`, patched/check/submitted | accepted and sealed; hidden pass post-seal | clean recurrent observation success |
| Alpha/223607 T25 B | exact 198-line extents and 12-call budget | selected correct observation/patch, then 50-line pages | budget ended after call 12 | page-size policy failure, not missing information |
| Beta/223607 T25 C | same stale/current competition under seed 223607 | selected current observation; two redundant confirmations; correct closure | accepted and sealed; hidden pass post-seal | semantic success with avoidable acquisition cost |
| all C50 B | full append-only chronology and correct current world | correct Phase-B mutation/check/probe/reads | denied next request at 50,176 physical envelope | append-only control physically nonviable before Phase C |

## Cross-trajectory findings

### Candidate-bound observation validity is model-usable

The key new result is positive. On both trajectories that reached Phase C,
Qwen chose the current observation solely from familiar action/target labels
and exact candidate bindings. It never reopened the stale observation. It then
used the exact current marker in an observable, hidden-correct mutation.

This is stronger than closed-case comprehension. The actor generated the
handle choice in an open coding loop and connected it to a later candidate
effect.

### Purpose continuity remained strong

After every reset, private reasoning named the correct active phase and did not
restart completed archive or stage work. The exact active-step pointer remains
empirically load-bearing through a second transition.

### The remaining weakness is local action policy

The actor often repeats the entire checklist in private reasoning. That helps
stage tracking, but it does not reliably optimize action cost. The two Alpha
failures and the extra Beta Phase-C reads all arose after Qwen already possessed
and articulated the necessary fact.

More reasoning is not presently earned as the remedy: the failures occurred
with bounded reasoning enabled, and their causes are legible in the saved
traces. The more precise hypothesis is that a low-value page-size/confirmation
decision is consuming scarce action and context budget.

### Context economics

Across all four cells, C50 spent 832,027 Phase-B prompt tokens and 2,596 seconds
of endpoint compute, yet none reached `fork_ready`. T25 spent 246,350 Phase-B
prompt tokens; the two successful branches then spent another 46,999 tokens in
Phase C and completed the study goal.

For the two Beta cells individually, complete T25 Phase B+C used 65.2% and
61.1% fewer prompt tokens than the corresponding incomplete C50 Phase-B paths,
and 33.2% and 18.5% less endpoint compute time. These are descriptive paired
economics, not a population estimate, because C50 never completed the task.

## Falsifiable hypotheses earned by the audit

1. Candidate-ID bindings plus exact reopen are sufficient for current-versus-
   stale selection when the actor reaches the decision point.
2. Exact purpose projection remains sufficient through at least two resets;
   persistent semantic summaries are still unearned.
3. The dominant recurrent reliability limit is low-level acquisition policy,
   especially actor-selected page size and redundant confirmation.
4. A read contract that returns the largest exact bounded page with an explicit
   continuation—removing `line_count` as a model decision—will improve closure
   without changing semantic information or introducing host relevance.
5. Additional private reasoning alone will not remove the failure, because the
   current reasoning already identifies the correct fact and remaining steps.

Hypothesis 4 is the highest-value narrow follow-up. It should be tested on
fresh development material before any further recurrent primary run. No
relationship graph, summary, embedding, or richer metadata layer is earned.

