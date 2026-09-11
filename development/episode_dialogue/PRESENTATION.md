# The input change earned by this conversation

Qwen proposed one `episode_annotation` beside `active_user_authored_step.text`.
Its example correctly calls the report presession and EVT-0011 an attempted
repair, without declaring behavioral success. The actual proposal and full
thinking are preserved in [E2](turn-02/calls/E2-assistant-content.txt).

Retain the single annotation and placement. Revise the example for use across
turns: do not hardcode EVT-0011, abbreviate the original task with an ellipsis,
or copy a snapshot's lack of verification into a persistent status message.
The existing event frame already supplies actual actions, results and version
bindings. The added annotation states only the relationship supplied by the
task author:

> Task-author context: the problem reported in task and this step's text precedes this repair session. active_phase_event_frame records this session's actions and results. Repetition of the report is not a new observation after those actions.

This annotation is preparation-authored context, not a new literal owner quote,
model-written account, inferred diagnosis or replacement for the task. Existing
`text`, `host_inference`, identifiers, source, tool requirements, action grammar,
resource state and all event/check data remain unchanged. The scope must be
established when preparing a task; it is not automatically inferred for every
user message or for histories with a different episode relationship.

## Concrete ordinary-action inputs

The [preparation helper](../../scripts/prepare_episode_framing.py) adds exactly
that field to a copy of an ordinary action request. The next fresh task's request
preparation must call `annotate(request, report_precedes_session=True)` on each
evolving input after establishing that scope, then perform its normal native
rendering, tokenization and admission. This is an explicit prospective
presentation choice; the frozen pilot runner and host remain unchanged.

These complete examples use actual saved task states, with only the annotation
added. They have **not** been sent to Qwen:

| Example | Preserved dynamic state | Prospective native input | Added tokens |
|---|---|---:|---:|
| [Before work](examples/L02-001-request.json) | Empty event history; original candidate | 3,120 | 50 |
| [After the repair](examples/L02-012-request.json) | Accepted event 11; no check in the frame | 17,982 | 50 |
| [After the check](examples/L02-014-request.json) | Actual passing check bound to the successor | 20,077 | 50 |

Native examples are derived by replacing the one user message inside its exact
saved native rendering and independently counting with the pinned tokenizer.
They are not new server-rendered or model-exposed evidence. Actual future inputs
still require native preparation. Offline comparison of all 24 original pilot
requests confirms that removing the added annotation restores every original
field, including output constraints, source, candidates and checks. The helper
also rejects undeclared scope, duplicate annotation and conflicting task/step
text. See [FRAMING_VERIFICATION.json](review/FRAMING_VERIFICATION.json).

## Carry it into task work and judge use

The next fresh investigation should include this annotation from its first
ordinary action input through closure. Choose a task outside the agent/metadata
domain with useful navigation and accessible evidence distinguishing plausible
explanations. Prepare the task, behavioral checks, action allowance and physical
input/generation capacity before its separate execution decision. Do not add an
isolated wording comparison or rerun an exposed pilot cell.

During that task, inspect what Qwen makes of the original report after an
accepted edit and after an actual check result. It should distinguish the old
report from a new observed failure, use the actual current-candidate check
status, and neither infer verification nor require a reread from the annotation.
Correctly resolved questions, extra executed work and sustained mistaken
associations are different outcomes. Preserve actual prompts, complete thinking,
actions, results and next inputs before making those judgments.

E2 shows an informed explanation after clarification. It does not establish that
Qwen uses this revised annotation during work. That transfer remains the next
empirical obligation. Domain/task/framing changes together cannot establish a
framing-only effect. A working account remains an option if evidence earns it;
the annotation makes no claim to retain the model's investigative rationale.
