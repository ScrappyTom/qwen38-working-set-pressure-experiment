# Saved dispatch continuation: correct code/tests, documentation gap

The uncoached dynamic001 run under 1c942cab closed with its registered-check pass
and submission. Qwen reacquired the saved implementation, diagnosed union-member
ABC token initialization, saved a targeted repair and two meaningful regressions,
used a real documentation failure, corrected it and consumed its current pass.
Earlier first-job work survived. Direct review found that the checker environment
and prose still prevent calling the standalone documentation complete.

The original seventeen-request result and all observations remain unchanged.
A separately declared documentation job addresses the findings; there is no
retroactive regrading, live coaching or silent restart.

## Actual contribution and evidence

The only library change initializes the existing cache token if any registered
union member has __abstractmethods__, retaining ordinary-class initialization.
Dispatch and MRO lookup remain unchanged. A union object lacks that ABC attribute,
although its ABC member has it; the dispatcher must monitor later global token
changes to invalidate the cached default. The saved code preserves prior member
validation and atomic registry updates.

Two new tests isolate their ABC/Payload/dispatcher per method. Each warms default
dispatch for the same Payload instance, checks the concrete int member, performs
ABC virtual registration without another dispatcher registration/cache clear,
and requires the union handler and continued int behavior. Both union forms are
covered. Both tests pass on the saved code and fail on the historical merged
union implementation. These are meaningful regression methods, not two independent
model investigations.

The repeated frozen check passes 24 original methods, 8 independent feature methods,
5 preserved authored methods, 7 independent dynamic methods and 2 new authored methods.
Its fourteen doc examples pass in its original environment. All five protected
files, including first-job tests, remain exact. The four new accepted versions
bring the lineage to eleven. Post-seal repetition confirms reproducibility,
adding no distinct behavioral coverage.

## Direct transition trace

| Requests | Actual support and decision | Effect |
|---|---|---|
| C16–C20 | New task, released source inventory, old pass/new-definition mismatch; ordinary current acquisitions | Full actual saved library reacquired; no historical body grants authority. Root navigation repeats already shown structure. |
| C21–C23 | Current register/dispatch/MRO source | Precise union-object/member distinction saved in account; C22 explicitly uses it alongside source. New test/doc targets located. |
| C24 | Exact visible old token condition/current guards | Targeted library successor ff91f22e saved and refreshed. |
| C25–C27 | Current implementation, test/doc skeletons | Long future-work rehearsal precedes navigation and a three-line read; then two real tests saved on f3a7aa69. |
| C28 | Current doc region and actual test successor | Literal SOURCE replacement saves exact document f98f85e3. Private invalid-union decorator premise is corrected before saving; bare ABC return assumption persists. |
| C29–C30 | Complete current check failure at doc line 47, returned `<class 'Payload'>` | The exact diagnostic reaches the actor. It patches the expected output to that literal class display. |
| C31–C32 | Applicable pass on 2d4a20cf, correct current identity | Actor consumes actual pass, updates completion account and submits unchanged. |

All 26 nonterminal receipts reach their following input. No current-source loss,
capacity rejection, selected-group replacement, historical recovery, physical
truncation or live intervention occurs. The initial release is evaluator-controlled,
not natural pressure. Code/tests remain co-present through documentation work.

## Post-seal apparatus and prose findings

The checker directly called DocTestParser with only `functools` in globals.
Payload.__module__ consequently becomes `builtins` and prints `<class 'Payload'>`.
Installed Python3.11.4 doctest.testfile explicitly defaults __name__ to `__main__`.
Matched CPU probes of the exact saved document yield 0/14 failures with the original
unset namespace and 1/14 under `__main__`, whose output is `<class '__main__.Payload'>`.
The observation was preserved faithfully, but its environment did not match the
normal standalone examples. Copying that observation repaired the frozen check,
not portability. See documentation-probe/RESULTS.json and exact outputs/source.

The introduction's unqualified 'selected whenever' rule is also false: on the
saved library, register `int | str` to a union handler then `bool` to another handler.
Although `bool` is an `int` subclass, True selects bool-specific; int/str still select
union. Prose must respect normal more-specific selection. No source change occurs
in this counterexample. A doc-example pass does not endorse surrounding claims.

Both findings earn documentation_continuation/PLAN.md: correct the namespace in a
derived checker, protect the actual code/tests and run a declared review-directed
prose job. Preserve both original packages and their scores. Do not add another
memory representation or silently edit the model's work.

## Accounts, costs and limits

C21's account preserves the decisive member/object distinction; C22 explicitly
uses it. The governing source is still visible, so this is account use alongside
source, not isolated benefit or substitution after eviction. C26 records completed
library work and pending contribution. Later accounts shorten that explanation;
the terminal account is current to the actual check but omits why the repair was
needed and overstates completion of prose obligations. Freshness, usefulness and
semantic truth remain separate.

The continuation uses 17 new requests / 28 operations and 255,514 input / 56,212 generated
tokens. Model-request time is 63.811 minutes; loop time 67.388 minutes. The lineage
uses 32 requests / 51 operations and 148.908 model minutes across two unlike jobs.
C26 generates 12,592 tokens to record an account/read three doc lines; C27 generates
13,373 before saving the tests. Useful analysis, repeated reconstruction, inaccurate
private premises and transport work coexist. No causal cost allocation is established.
The final closure is brief, showing that costs differ across task stages.

Maximum sent input 19,867; maximum input-plus-output 31,124 in 56,576 physical context.
No response exceeds the 32,768 planning reserve; this does not bound future uncapped
responses. FullGPU/q4/noMTP/medium settings remain fixed, with 164 MiB advisory
minimum free GPU memory. No CUDA failure or truncation is recorded; owned runtime
closes and port is free. These data do not establish a cause for earlier slow prompt processing.

Exact verification passes 482 artifacts / 930 bindings / 419 custody records and 30 checkpoint
restorations. All complete thinking/public outputs, actual inputs, source/effects
and artifacts received direct review. Preparation/helper completion requests: 0.
Native rendering, CPU qualification and reviewer effort are outside model-request
minutes; reviewer effort is not independently timed. Read READING_NOTES.md,
VERIFICATION.json, ARTIFACT_AUDIT.json and the documentation probes.

The wider workload/pressure programme remains open. This supplies a useful saved
code/test continuation and feedback-to-correction path, with a concrete apparatus
and prose gap. It does not establish general reliability, autonomous account
maintenance, natural-pressure continuity or a speed advantage.
