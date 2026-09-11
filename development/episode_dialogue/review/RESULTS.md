# Results — learning with Qwen about episode confusion

The requested conversational step is now real: Codex asked Qwen about the actual
confusing input, preserved its interpretation, responded to it with source-checked
clarification and asked for a small presentation suggestion. Both complete
thinking/final responses were read. The completed pilot was not assisted,
rewritten or repeated.

Before clarification, Qwen correctly distinguishes the report container from
recorded work, but still regards the report's accepted edit as possibly the
actor's EVT-0011 repair. It recognizes that no subsequent failure/check is
actually recorded. This matters: exact version tracking and distinct containers
have not made the episode association explicit.

After clarification, Qwen suggests one annotation beside the report. Its example
identifies the report as presession, the recorded edit as an attempted repair,
and the repeated task text as no new failure observation. It uses the corrected
real candidate/diff paths and does not treat source reconstruction as a test.
That is informed conversational design input, not proof of the original cause.

## The resulting decision

Retain Qwen's single annotation and placement. Codex prepared an explicit
[model-facing input change](../PRESENTATION.md), including complete ordinary-action
requests before work, after mutation and after a passing check. A reusable
preparation helper adds only the task author's episode relationship; it does
not repeat a fixed event number or manufacture a verification status. It keeps
the full task, complete tool reference, state and action constraints intact.

The exact wording is:

> Task-author context: the problem reported in task and this step's text precedes this repair session. active_phase_event_frame records this session's actions and results. Repetition of the report is not a new observation after those actions.

All 24 archived requests pass the offline annotation-only comparison. The three
saved examples each add 50 input tokens in CLI recounts of derived native inputs.
The examples and Codex's revised wording have **not** been sent to Qwen. This
tranche establishes consultation and concrete preparation, not task-level use
or a measured performance benefit.

Use this presentation in the next fresh ordinary investigation and inspect its
use through actual edits and check feedback. Keep a new domain as a practical
task choice, not a substitute for explicit episode framing. The exact task,
checks, allowances and native capacity still need concrete preparation before
the next separate execution decision. Do not open another isolated wording
comparison merely to obtain a favorable result.

The hypothesis to test in task work is concrete: after its own repair, Qwen
should interpret the repeated report as the original incident and take new
success/failure evidence from actual candidate-bound results. If it continues
to associate the report with its repair despite that context, preserve the
trajectory and discuss that actual misunderstanding with it separately. Correct
within-response resolution is different from extra operations or sustained
confusion. Do not attribute a changed result solely to framing if the task also
changes, or adopt a working account before identifying the evidence need.

## Costs and limits

| Turn | Input tokens | Generated tokens | Request seconds | Actual action |
|---|---:|---:|---:|---|
| Interpretation | 18,173 | 12,756 | 791.391 | None; prose only |
| Adaptive design reply | 22,674 | 7,297 | 487.281 | None; prose only |

The two turns cost 21.31 model-request minutes. Long deliberation persists even
with full tool information and a focused question. The final second answer is
shorter, but the tasks differ, so no controlled efficiency inference follows.
Both calls complete on the same q4/56,576/no-MTP/xhigh/uncapped preset, minimum
free GPU memory 339 MiB under the accepted advisory policy. No pressure boundary,
tool execution, failed repair or new capability result occurs in this dialogue.

The first question already directs attention to the episode distinction; the
second supplies the intended association. Retrospective explanations are not
privileged access to earlier causes. E2's exact snapshot example was source
checked and then revised for prospective use, not adopted as an authority.

Read the [execution receipt](EXECUTION_RECEIPT.md),
[host-path audit](HOST_PATH_AUDIT.md), [apparatus finding](APPARATUS_FINDING.md),
[complete direct audit](DIRECT_TRANSCRIPT_AUDIT.md),
[evidence verification](VERIFICATION.json) and
[framing verification](FRAMING_VERIFICATION.json).
