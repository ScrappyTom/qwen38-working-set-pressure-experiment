# Shift Ledger: a completed task with the consulted episode framing

Qwen completed S01 in **11 actions**, made one correct reporting repair, passed
all **24 public cases on its first check**, and submitted that same candidate.
All 11 complete thinking/final responses were directly reviewed after sealing
and verification. All ten nonterminal results entered the next actual input.
The run used the approved q4/56,576, no-MTP, uncapped-xhigh configuration.

The conversational development loop now reaches actual task work: the earlier
separate Qwen dialogue informed a source-checked episode annotation, which was
present in every live input here. After its patch, Qwen explains the original
omission using the old containment logic, identifies its own overlap repair as
performed work, and runs a new check on the successor. After the passing result,
it recognizes that no later edit occurred and submits. The previous oscillation
between the reported incident and a failure after its own repair is not observed.

This is behavior consistent with the intended distinction. Qwen does not
explicitly refer to the annotation, and the task/domain also changed. Neither
success nor absence of the old confusion establishes causal use of that sentence
or a measured framing improvement. The stronger supported observation is that
the consulted presentation was actually exposed during a complete working loop
and did not prevent useful, correctly bound actions.

## What the trajectory exercised

| What Qwen saw | What Qwen did | What the host did next | Interpretation |
|---|---|---|---|
| Root orientation, then newly discovered nested directories | Three different directory pages, each following a visible child path | Returned each listing and included it in the next input | Useful navigation; no repeated parent page or compulsory completion loop |
| README, exact window and reporting source | Identified containment versus overlap, then read the model and API | Returned those exact files without changing candidate identity | Source-led investigation; no failed diagnostic or experimentally rejected alternative |
| Complete target source and current pre-edit guards | Replaced full containment/full duration with positive overlap duration | Accepted one patch and returned exact successor/diff | Correct repair, different bytes from the preparation oracle |
| Original report plus annotation, historical source and actual accepted patch | Reconstructed the original defect and selected a successor-bound check | Ran public check; all 24 cases passed; delivered the complete result | No new post-repair failure invented from repeated task text |
| That passing result bound to the unchanged current candidate | Declined another check and submitted | Accepted checked submission and closed the run | Current verification governs closure |

The repair computes `min(shift.end, window.end) - max(shift.start, window.start)`,
skips nonpositive overlaps and aggregates the remaining minutes. Direct final
source review confirms preservation of confirmed-status filtering, additive
employee totals and sorting. Window construction and input validation are
unchanged. Public cases cover offsets, clipping, exact/touching boundaries,
spanning shifts, void rows, fractional minutes and specified invalid inputs.
This is bounded behavioral acceptance, not universal correctness or a hidden grade.

## Costs, opportunity and remaining friction

| Measure | Observed |
|---|---:|
| Actions: navigation / reads / patch / check / submit | 3 / 5 / 1 / 1 / 1 |
| Model-request time | 606.263 s (10.10 min) |
| Task-loop wall time, excluding runtime startup/closure | 612.250 s (10.20 min) |
| Cumulative native input tokens | 68,794 |
| Generated tokens, endpoint accounting | 8,781 |
| Initial / peak native input | 3,193 / 10,543 |
| First check, actions available before / after it | action 10; 11 / 10 |
| Actions remaining after submission | 9 |
| Minimum sampled free GPU memory | 335 MiB, advisory policy |

No rejected action, failed check, duplicate acquisition, post-change source
reread, historical retrieval, capacity denial or externalization occurred.
The first check leaves ten actions; this is actual action allowance, not a
guarantee that an arbitrary future correction would fit the native input ceiling.
There is no observed after-failure opportunity to report.

There is still substantial deliberation cost. Response 9 uses 4,000 generated
tokens and 228.422 seconds (45.6% of generation; 37.7% of request time). It
repeatedly considers reading the importer, revalidates the same overlap repair,
rehearses guards/JSON/one-action constraints and checks equivalent edge cases.
Response 10 spends another 1,317 tokens deciding between more inspection and
testing. Both eventually take useful actions, without the contemplated rereads.
Not all edge-case reasoning is redundant, and its avoidable share is unmeasured.
The complete reference is already present; this is not evidence of missing
argument requirements, a context-loss event, or justification for a thinking cap.

Qwen briefly questions whether prior exact source is still usable, then correctly
uses the unchanged file identity. It sometimes uses loose phrases such as
having read the main files or referring to the previous repair as a prior session;
it also explicitly recognizes the unread importer and the actual current check.
These phrases do not produce false coverage, a new reported failure or an extra
operation. Preserve them as limited observations, not a diagnosis of confusion
that persisted into the actions.

## Decision and next useful work

Retain the complete tool reference, accurate resource/navigation wording and
consulted episode annotation for subsequent preparation. This is continued use
of the documented interface, not another performance promotion or host refactor.
The run earns no new metadata/tool patch. Keep accurate object grouping and a
working account provisional; this trajectory neither needs nor rejects them.

The next useful preparation is an investigation where accessible evidence can
change the explanation during work. The present small task is solved from
conspicuous source logic before any check, so it does not exercise correction
after failure or an evidence-driven reversal. Do not add seeds to this consumed
run, force an initial mistake, pad source, or manufacture a pressure boundary.
Any future consequential misunderstanding should again be preserved, diagnosed
and examined in a separate adaptive conversation with Qwen before changing the
presentation. Long reasoning alone does not identify which change would help.

Concrete hypotheses for future task preparation: (1) after an actual failed
successor check, Qwen should associate that failure with the checked candidate
while keeping the old report presession; (2) evidence contradicting a live
explanation should change subsequent investigation under unchanged premises;
(3) any repetition must be separated into new-evidence confirmation, necessary
reacquisition and repeated work on still-available facts. A task must make those
observations possible without telling Qwen which explanation to reject.

All history remained resident and peak input was only 10,543. Prior private
thinking was omitted immediately, while source/action/result evidence persisted.
No 25k contrast, natural pressure continuity, memory mechanism, generalized
speedup or reliable cross-task efficiency is established. The one approved
attempt is consumed; its unused nine actions authorize no successor.

See the [direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md),
[host-path audit](HOST_PATH_AUDIT.md), [apparatus finding](APPARATUS_FINDING.md),
[execution receipt](EXECUTION_RECEIPT.md), [verification](VERIFICATION.json)
and [decision](DECISION.json).
