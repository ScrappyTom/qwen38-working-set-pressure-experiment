**Project assessment — 9 September 2026**

My assessment is that this project has established a useful mechanism for continuing specified coding work under context pressure. Its strongest result concerns exact evidence, current state, and execution continuity. Its evidence for independent investigation, evolving plans, or general long-horizon reliability remains limited. Two new offline findings also narrow what should be inferred from the latest all-pass result.

The active project is `qwen38-working-set-pressure-experiment`, paused at commit `4a800ba` after Experiment 020. The earlier metadata repository is an evidence predecessor, at `9b48ee4`. Both Git working trees were clean when inspected. This review is an additive assessment; it does not change frozen results or experimental code.

I read the checkpoint, controller record, operating rules, current specification, Experiment 020 results and audits, earlier transition results, and relevant host, tool, grading, and test code. I directly examined saved model-facing requests, private reasoning, JSON actions, and exact tool results for the behavioral examples below. I also verified custody and endpoint/action equality across the complete latest run. This is a targeted independent project review, not a claim to have repeated the existing exhaustive human-readable audit of every historical transcript or reread every repeated source body in all 106 latest requests.

The central evidence is in the [pause checkpoint](PROJECT_CHECKPOINT_2026-08-30.md), [controller record](EARNED_CONTROLLER_V1.md), and [Experiment 020 results](experiments/020_owner_controlled_ecological_pilot_v2/RESULTS.md).

**What is working**

The architecture separates three useful things: a record that something happened, a binding identifying which candidate or file it concerned, and the exact content needed to act. That separation is supported by observable behavior. In Experiment 020 cell 03 X25, the first post-pressure request retained the identities of the current observation and the earlier verifier source read, while both bodies were absent. Qwen selected `OBS-0002`, then `RES-0002`, recovered their exact bodies, made the two verifier repairs, checked the current candidate, and submitted. The saved request really contains the external-body state; this interpretation does not depend on taking the model's explanation at face value.

Canonical reopen addresses also work as intended in this example. The new access events retain `OBS-0002` and `RES-0002`; they do not create a chain of result-of-result addresses. This preserves provenance without deciding relevance for the actor. The [saved first X25 request](experiments/020_owner_controlled_ecological_pilot_v2/measured_run/cell-03/X25/transcript/001-coding-request.json) and [reopened source result](experiments/020_owner_controlled_ecological_pilot_v2/measured_run/cell-03/X25/transcript/002-result.json) show that sequence directly.

The reported latest outcomes reproduce under the frozen graders:

| Latest experiment | R50: exact bodies resident | X25: old exact bodies externalized |
|---|---:|---:|
| Checked submissions passing the frozen hidden grader | 4/4 | 4/4 |
| Conceptual calls, including each paired shared prefix | 67 | 79 |
| Cumulative prompt tokens | 1,229,046 | 1,227,723 |
| Peak prompt range across trajectories | 27,908–35,335 | 20,544–20,940 |
| Completion tokens | 30,311 | 34,911 |

These are two tasks, each with two seeds and two conditions, not eight independent tasks. There were 106 physical completions because shared prefixes executed once. X25 reduced each pair's peak prompt size by 25–41%. It used 17.9% more conceptual calls, essentially the same cumulative prompt tokens, and 15.2% more completion tokens. The reported endpoint-time difference was only 1.3%, unfavorable to X25.

This distinction between peak occupancy and cumulative work is one of the project's most useful findings. Externalization buys room to continue. Its value does not require every individual task to become cheaper. Experiment 018 supplies the complementary published result: R50 stopped at physical capacity in all four trajectories, while X25 continued all four and finished the two observation trajectories. I treat that earlier result as reported evidence, rather than claiming a fresh full audit of Experiment 018 here.

The experimental custody is also a substantial asset. I independently verified all 1,625 files in the latest response seal and all 12 run-segment record chains. All 106 saved assistant actions and reasoning fields matched their raw endpoint responses. I reconstructed the eight terminal candidates from custody and reran their frozen hidden graders; all eight passed. An independent line-coverage check found zero missing required source lines before the first mutation in each branch. These checks support preservation of the recorded result despite the new limitations below.

**What is not working, or is weaker than the prose suggests**

1. **The grader misses a real boundary difference between successful candidates.** The owner-facing task says that `max_files=N` admits at most the first N eligible files. Both saved R50 source repairs append a file before checking whether the limit has been reached. With one eligible file and `max_files=0`, both return one file. Both saved X25 repairs check the limit before the append and return no files. The admitted donor also returns one file at zero. All four candidates still pass the frozen grader, which tests `max_files=1` but never zero.

   This is an uncovered contract edge, not a retrospective replacement of the frozen score. If zero was intended to be outside the API domain, that restriction was not stated in the model-facing task or enforced by the function. The practical lesson is that donor equivalence and hidden-test success are narrower than complete semantic correctness. There is no basis to infer a general X25 quality advantage from this small post-hoc probe.

   The [source hidden grader](experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank/evaluator_only/E20-SOURCE-IMPORT-BOUNDARIES/hidden.py#L16) and the [R50 repair action](experiments/020_owner_controlled_ecological_pilot_v2/measured_run/cell-02/R50/transcript/005-assistant-content.json) make the distinction reviewable.

2. **The post-hoc inspection audit can falsely report a complete read.** In an offline probe through the actual `Candidate` and `ToolExecutor` implementations, a legal 4,000-line file was read at lines 1–3,000 and 3,999–4,000. The tool correctly left `complete_reads` empty. However, `inspection_status` reported `all_completed_before_first_mutation: true`, overlooking the 998 unread middle lines. Its predicate checks that the first coverage range starts at line 1 and that some read reaches EOF; it does not require continuous coverage between them.

   This is an actual audit defect in [inspection_status](src/working_set_exp/ecological_pilot_v2.py#L293). It did not affect the saved Experiment 020 inspection outcomes: I checked their line coverage independently and found no gaps. It becomes material when larger files require several pages. The defect earns a narrow prospective audit correction, without a new memory mechanism.

3. **Correction headroom is qualified for an ideal path, not maintained throughout execution.** Cell 02 X25 reached its first public check with three calls remaining, including that check. A failed check followed by patch, recheck, and submit requires four. The check happened to pass, so the trajectory completed, but it no longer had a full correction cycle available. The resident resource text carefully says the cycle fits the prospective ideal path; it should not be interpreted as a runtime guarantee. See the [actual check request](experiments/020_owner_controlled_ecological_pilot_v2/measured_run/cell-02/X25/transcript/013-coding-request.json).

4. **The implementation is still a bounded research apparatus.** Current candidate admission permits at most 256 files, 24,000 bytes per file, and 512 bytes per source line. The patch schema limits each old/new fragment to 512 characters. Experiment 020 has one active phase and a 24-call limit. These constraints are reasonable for controlled measurement, but they matter before treating the controller as something that can directly ingest an arbitrary repository or support an indefinitely long investigation. Externalizing bodies also does not bound the growth of the resident event identities themselves. See [candidate admission](src/working_set_exp/candidate.py#L11) and [patch schema](src/working_set_exp/tools.py#L444).

5. **Some project scaffolding reflects an earlier phase.** Of 35 selected offline test functions/methods I executed, 34 passed. The one failure asserts that Experiment 020's authorization file does not exist, although that authorization was subsequently created and consumed. The existing apparatus report already acknowledges deselecting this test. It is lifecycle maintenance debt rather than an actor or controller regression. The README also still calls Experiment 012 the latest study in one older paragraph. These do not undermine the saved evidence, but the next maintenance pass should distinguish historical preconditions from current regression checks.

**What the task setup actually tests**

The source prompt names all 11 required paths and explicitly supplies the four boundary semantics. The observation prompt names all 10 required paths and explicitly describes both safety fixes, including the timeout range and default. It also tells Qwen to choose the observation using exact candidate binding. The directory contains one clearly older observation and one current observation with a descriptive verifier-safety label.

None of the 106 recorded actions uses `p0_page`, `tree`, or `search`. The action totals are 60 reads, 23 patches, eight checks, eight submissions, three result reopens, and four observation reopens. Thus the latest result does not exercise autonomous P0 discovery, and it cannot isolate the causal value of the observation body: much of its actionable meaning is already in the task. The model does use the exact source and observation correctly, but necessity of each information component is a different claim.

The inspection requirements use real source and create real measured pressure; they are not duplicated filler. However, requiring every named audit file to be read before mutation creates the workload that crosses the boundary. This is a valid controlled audit task, with a narrower ecological claim than a developer independently finding an unknown bug in a large repository. Most of the retained complexity is factual execution state. The experiments have not yet shown preservation of a changing explanation, rejected alternatives, or a self-generated multistage plan.

**Further insights from the actual interactions**

“Rereading” is not one failure category. In cell 03 X25, reopening the old verifier body is appropriate because that body has left the prompt. Knowing that a read happened does not supply the source text needed for an exact replacement. After a mutation, checking current source may also be reasonable because the earlier body belongs to the predecessor candidate.

Cell 04 X25 shows a more specific inefficiency. Qwen wanted `_bounded_timeout` but requested a read starting at line 258, just below that function. It then requested line 248 and obtained it. The second read followed an incorrectly placed first read. The transcript supports this narrower explanation more directly than a blanket description of both reads as confidence-building. The source body from before the patch and the patch diff were still resident, so another route to acting was available. This does not justify automatically suppressing reads; it does suggest separating absent evidence, source-version confirmation, targeting mistakes, and redundant confirmation when interpreting costs.

There is also a clear evidence-to-action gap even in the successful resident condition. Both source R50 seeds identify the correct boundary errors in their private reasoning, but their first patch targets an unrelated file prefix: one adds a blank line and the other is an exact no-op. The host accepts the byte change and rejects the no-op. Both actors then recover. Correctly stated reasoning therefore does not prove a correct or efficient next action. These examples do not isolate whether the reasoning cap, action schema, or model policy causes the mismatch, and they do not earn an automatic increase in reasoning budget.

The strongest architectural insight is that reliable progress needs validity and ordering as well as content. The earlier recorded progression—from losing completed reads, to receipts, to one ordered event representation—supports that direction. It also explains why adding more metadata indiscriminately was unproductive. The predecessor's Experiment 001F reports that an optional exact-evidence action was never selected and added 9.49% prompt cost. A capability can be accurate yet lose to a simpler source read. That is a useful design lesson, without concluding that all richer evidence interfaces or all semantic memory are intrinsically ineffective.

**What I would prioritize when this resumes**

First, preserve the current results and document the newly found checker boundary and coverage-audit defect as prospective corrections. Test acceptance semantics independently of the donor, and distinguish ideal-path reserves from the action opportunities actually remaining at the first check. These are earned improvements to measurement.

Then keep the information representation substantially unchanged and select one fresh task that requires an evolving investigation: a reproducible failure with two plausible explanations, evidence ruling one out, and authentic context pressure before the final repair. The distinguishing outcome would be whether the actor preserves the rejected alternative and the reason for the next experiment, while still grounding its final change in exact evidence. Avoid combining that with dense observation choice and purpose revision in the first task.

For that evaluation, count task success, first-check failures, correction capacity, repeated rejected hypotheses, necessary reacquisition, and avoidable repeated work separately. Keep the paired resident/externalized comparison and report peak occupancy separately from cumulative calls and tokens. The program has enough evidence to test whether the same architecture supports harder work. It does not currently have evidence that another memory representation is the next necessary feature.

Verification in this review was offline. No actor inference, server launch, new experimental run, or modification of frozen evidence was performed. The 35 selected checks were executed with Python's unittest runner and direct calls to the plain test functions; this was not a full pytest-suite run. The response seal file hash is `97e32a24fbeeb7c867f977e460e00daaf1d7e25bad33ead2f81f44c6c28a9076`; its file-list aggregate is `5c9f3f3d59ff9adea3e13b0dffc9c68ae45dcb18b078859495db597764e29e95`. The differing hashes in the two existing audit documents refer to those different objects.
