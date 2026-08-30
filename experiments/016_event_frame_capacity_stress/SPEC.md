# Experiment 016: Offline Event-Frame Capacity Stress

## Purpose

Test the exact Experiment 015 event-frame encoding against the largest already
qualified active-phase schedule before any fresh large-world fixture is built.
This is an offline contract qualification, not a model-behavior experiment.

The maximum active-phase schedule is sixteen accepted actions because sixteen
is the largest phase budget already qualified by Experiment 014. A future
phase with a larger budget requires a new capacity proof.

## Stress cases

Two sixteen-event candidate-bound patch sequences are constructed through the
real `Candidate` and `ToolExecutor` implementations:

1. maximum-schema ASCII fragments: both patch fragments contain 512 ordinary
   source characters, the model-facing schema maximum;
2. reasoning-budget-compatible escaped-control fragments: both fragments
   contain 170 UTF-8 control characters. Their strict JSON actions remain below
   the 5,000-byte host cap, and each exact action plus the full 512-token private
   reasoning allowance remains below the 2,500-token completion allowance,
   while exercising the tokenizer-expensive legal escape form.

Every action must be accepted by the actual host. The successor candidate ID
from each result must bind the next action.

## Conditions

For each stress sequence, render:

- all exact result bodies resident;
- all exact result bodies external behind their existing `RES-nnnn` handles.

Apply the pinned exact tokenizer and both existing admission envelopes:

- X25: adjusted prompt plus 2,500 output tokens must be at most 25,000;
- R50: adjusted prompt must be at most 47,000 and adjusted prompt plus output
  must fit the physical 50,176-token slot.

Measure actions, structural results, result-body fields, resident events, and
externalized-result events separately. Token component sums are descriptive;
the complete rendered request guard is authoritative.

## Gates

The current event frame passes only if a sixteen-event legal sequence can be
admitted after all old result bodies are externalized. A counterexample is
sufficient to reject the representation for large-world R50/X25 use.

Also verify:

- contiguous event identity;
- exact resident result reconstruction;
- exact external result custody;
- phase-scoped sequence restart without overwriting the prior phase.

## Authority boundary

No GPU call, endpoint request, model-server launch, fresh measured fixture, or
large-world successor execution is authorized. If the current encoding fails,
only a narrowly earned representation change may follow. Any such change must
receive renewed offline capacity and live placement qualification before fresh
large-world measurement.
