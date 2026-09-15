# Information, operations, and the model's working set

This is the stable architecture map for the development host. It describes the
implemented system and its open questions; it does not redefine frozen experiments
or turn engineering qualifications into model capability evidence. The owner asked
for this map and an implementation plan on September 14, 2026.

## Purpose and boundaries

The objective is durable, correct contributions across changing information needs
and bounded model inputs. Exact recovery is a prerequisite, not the final outcome.

- **World:** information available to the system for the task within its declared
  boundary, including information created during work. This is an information
  domain, not a software component. A reachable external source is not evidence
  that its current contents have been acquired or examined.
- **Stored material:** preserved source versions, instructions, interactions,
  operations, results, representations, metadata, and work products outside the
  model's context. For external observations, preserve what was actually obtained
  and when, rather than treating a live address as immutable evidence.
- **Working set:** the complete information actually presented to the model in
  one call: instructions, visible tool requirements, selected material, state,
  history, and feedback. The proposed request, native rendered input, dispatch,
  and response remain distinguishable records. Server-side output constraints
  are not automatically instructions visible to the model.
- **Selected evidence group:** material designated to remain available across
  calls until selection changes. In this host, `ranges` and `saved` maintain that
  designation. It is only one contributor to the complete working set.
- **Working-set management:** host and model choices about what to obtain,
  arrange, retain, replace, and present as the task develops.

Compatibility names are not new architectural objects. The wire key `workspace`
contains a current decision view. Its `working_set` lists contain selected source
and saved records that are not already displayed in `latest_feedback`. Empty lists
there do not imply an empty complete working set or an empty selection. Keep these
existing keys while explaining their scope; no storage or schema migration follows
from adopting the glossary.

## Information model

Material can have overlapping roles: task and amendments, source, interaction or
operation evidence, derived representation, working account, relationship note,
proposed work, and saved work product. An operation result can later become source.
A rejected action can preserve useful proposed code without becoming a saved edit.

The implementation preserves exact candidates, requests, responses, results,
diffs, state snapshots, and custody records. Ordinary task operations expose exact
source pages, navigation, saved action/result access, edits, checks, and submission.
There is no general model-written working-account operation in the current loop.
Thinking and discussion are archived but omitted from subsequent decision inputs.
Their omission is a policy choice, not evidence that an explanation was lost at a
later pressure boundary.

Current designations must agree with recorded changes and explicit decisions.
The host may persist snapshots and maintain mutable operational state; it need
not reconstruct everything from an event log on every call. Selection, task
amendments, and abandonment of a proposal involve recorded decisions, not event
order alone. A most-recent rejected edit is not automatically the intended next work.
The host can establish which account or artifact is designated current, but not
that its explanation or contents are correct.

## Metadata and relationships

Rich stored metadata and concise presentation are compatible. These are purposes,
not mandatory fields in a universal record format:

| Purpose | Mechanical facts and limits |
|---|---|
| Identity and address | Exact item/version/range and resolvable recovery reference. A valid address does not prove its contents support a claim. |
| Origin and production | Producing operation, actor, actual request/input and outcome. Preserve requested inputs separately from delivered inputs. |
| Representation and derivation | Exact source, excerpt, outline, serialized action/result, or authored account; identify the represented object and its source. |
| Scope and coverage | Requested versus returned range, paging continuation and examined scope. A page reaching EOF does not establish whole-file inspection. |
| Time and applicability | Observation time, candidate/file/checker bindings and the input at which capacity was measured. New versions can require reassessment without proving old conclusions false. |
| Task use and semantic relationships | Supports, contradicts, answers, or remains unresolved according to an attributed model/human account; these meanings are not mechanically certified. |
| Selection and presentation | What was selected, rendered and sent in each call. Historical delivery is not permanent current visibility. |

For a derived account, distinguish requested coverage, actual producing input,
and semantic adequacy. The host can verify the first two. Adequacy depends on the
intended use and requires reasoning, executable checks, or review. Exact wording
and exact provenance do not promote an authored interpretation into truth.

Relationships can belong to operations or calls rather than to content forever.
An unchanged file may remain applicable across another file's edit; a check also
depends on its checker definition. A capacity rejection belongs to the complete
proposed input at that attempt, not to the patch or candidate alone.

## Functional capabilities

| Capability | Current implementation | Qualified boundary and remaining gap |
|---|---|---|
| Store | Content-addressed candidates; action/result archive; raw requests/responses and custody logs. | Exact preservation and replay have extensive local qualification. Preservation alone does not make pending work usable. |
| Represent | Exact source pages, outlines, recent activity, selected saved records, current bindings. | Bounded mechanical representations exist. No general semantic account-maintenance policy is qualified. |
| Discover and retrieve | Tree/outline/search, paged history, RES result and EVT action recovery. | Exact routes exist, including grouped proposals. Choosing a resolvable handle can still obtain the wrong kind of information. |
| Assemble | Current view, selected source/result group, feedback deduplication, native input admission. | Host sizing and delivery have focused qualifications. Reliable selection of semantically sufficient supporting material remains unresolved. |

These are capabilities, not four required modules or four model calls. A read
can acquire, preserve, represent, and present source through one requested action.
The prompt builder implements Assemble.

Within Assemble:

1. **Reconciliation** updates current candidates, selected source views, check
   applicability, and recorded effects. A model's revised interpretation must be
   expressed and preserved separately; it is not derivable from a version change.
2. **Composition** chooses and arranges actual versions, extents, representations,
   and useful descriptions. The model currently selects relevance through reads
   and `work_on`; the host performs exact mechanical selection and deduplication.
3. **Admission and presentation** measure the complete native input, enforce the
   physical/input policy, preserve failures, and record actual dispatch. Enough
   input room does not guarantee adequate evidence or termination of generation.

Relevant code: [working session](src/working_set_exp/working_session.py),
[operating reference](src/working_set_exp/working_view.py),
[contribution checks](src/working_set_exp/contribution_session.py),
[reply execution](src/working_set_exp/contribution_reply.py), and
[actual request loop](scripts/run_uncoached_contribution.py).

## Host-model operating process

The model chooses and proposes operations. The declared host supplies exact
mechanics: discovery, sizing, source eligibility, version guards, execution,
requested successor checks, preservation, and truthful feedback. Semantic support
can be developed as a declared component when earned and evaluated; reviewers
must not quietly supply that component during an uncoached run.

Keep proposal, accepted execution, saved work, successful feedback construction,
actual presentation, interpretation, and checked completion separate. A rejected
patch preserves its proposed action without changing current work. This host
preflights edits on a clone before committing. Once another operation has actually
executed, a later presentation problem must not erase its outcome or imply it did
not happen. Retrieval reads historical evidence; it does not execute it again.

Qwen is the test pilot and a design consultant outside active runs. Preserve and
review the exact confusing input/output before a bounded consultation. Check its
interpretation against source. During runs, provide only declared input and actual
host feedback; no reviewer coaching, rescue, or action suggestions.

## Policies and modes

Selection, retention, representation changes, working accounts, grouping,
decomposition, capacity responses, and reasoning effort are variable policies.
A mode changes the working arrangement, not the world or the storage system.
An architecture map does not establish any particular policy as effective.

The present development configuration uses the declared medium/uncapped actor and
23,808 input ceiling within 56,576 physical context, with a prospective 32,768
generation reserve. The reserve is not an output guarantee. Frozen studies keep
their own configurations and results. Do not silently alter effort, input policy,
tools, or assistance while attributing a later result to one presentation change.

## Evaluation and immediate direction

Evaluate separately: physical construction/delivery; information available for the
decision; interpretation of that information; correct transitions and applicability;
quality and preservation of saved artifacts; termination; total inference, elapsed
time, and review cost. A passing host gate partly reflects enforcement, not an
independent demonstration of model judgment.

The [latest task](development/evidence_assembly/pending-contribution/review/RESULTS.md)
preserved a useful rejected proposal, but the actor recovered its rejection reasons,
released implementation support, and saved weaker tests. The
[subsequent consultation](development/evidence_assembly/selection-dialogue/RESULTS.md)
clarified selected-versus-displayed material and historical capacity after verified
facts were supplied. It did not demonstrate autonomous completion.

The [implementation plan](development/evidence_assembly/decision-state/PLAN.md)
carries those two earned distinctions into the shared operating reference and
qualifies real states and a scripted complete contribution. This is the first
implementation under this map. It does not solve semantic selection. The next
model evaluation should concern recovering pending work and its support, saving
and checking it, and preserving it through the next contribution. A working
account remains a possible, separately evaluated policy rather than a prohibition
or an automatic next feature.
