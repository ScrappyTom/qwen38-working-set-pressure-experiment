# Bounded navigation assessment

2026-09-22. Read-only review of artifact-map `run-001` C04–C10 during the live
attempt, extended with the completed C16 evidence below. No runtime, inference,
checker, implementation change or coaching. This does not assess the
still-developing attempt's final outcome.

## Evidence and limits

I read the exact wire messages, complete thinking/finals and actual results for
C04–C10, including `preceding_operation_feedback`, then inspected the current
working/decision/operable/recovery session renderers and small-repair specialization.
The candidate remains `0f67505a0ad439530ae16095fac49db730b34ca253794657e06273420c2ba872`
through these decisions. There are no selected source or saved-result bodies.

Directory and outline results arrive completely as latest feedback. They disappear
from the ordinary view after a subsequent operation; their recent rows preserve
path, operation, offset and RES/EVT handles, but not entries, total or next offset.
`current_p0` continues to show only the repository root. This is intentional view
construction, not a broken result delivery or a capacity stop.

The actual system message asks for the next useful operation and explicitly makes
paging optional. It does not require completing directory exploration before a
source read. The episode annotation also says repeated task text is not a new
incident observation.

| Decision | Actually visible | Final choice and implication |
| --- | --- | --- |
| C04 | Second directory page, nine files including `reopen.py`; recent row for the first page. | Reads the repository root again. Useful paths are present; this does not establish missing evidence as the cause. |
| C05 | Root; earlier directory rows without their entries. The account names candidate files. | Requests first directory page again. |
| C06 | First 16 of 25 files, `next_offset=16`; second-page historical row without entries. | Requests second page again. The already acquired counterpart is not in this input. |
| C07 | Second nine files, `next_offset=null`; account names three files to examine. | Requests first page again, after mentioning those known files. |
| C08 | First directory page. | Requests the `patching.py` outline, a useful advance to file structure. |
| C09 | Complete four-function outline, signatures, ranges and reusable SRC references. | Returns to the first directory page. The full useful outline is already visible, so retention alone cannot explain this choice. |
| C10 | First directory page; recent `patching.py` outline row without its body. | Requests second directory page again; the account says `patching.py` was paged without retaining its discovered function locations. |

The actual sent input counts are 5,243, 5,103, 5,457, 5,252, 5,455, 5,985 and
5,442 tokens, respectively, against 23,808. Canonically serialized result bodies
are 1,371 bytes for the first directory page, 869 for the second, and 2,336 for the
outline. These figures establish modest objects and ample observed headroom, not
the unmeasured native cost of a proposed combined view.

The actor repeatedly describes starting exploration and sometimes replaces a more
specific account with a general plan. Both current visibility and that account
content matter. Do not classify every repetition as a reaction to omission, or
infer that preserving a map will by itself produce source reading and an edit.

## C16: direct recognition of the omitted directory page

The later C16 input supplies complete `artifact_units.py` lines 1–459 and
`reopen.py` lines 1–83, with no selected saved results. The six recent rows are
EVT-0018 through EVT-0023. EVT-0020, the accepted C13 directory listing, is still
the third row: path `src/addressable_information_layer`, offset 0 and RES-0020
remain, but its entries, total and next offset do not. Latest feedback is read
EVT-0023; the extra preceding receipt is account EVT-0022. `current_p0` still
contains only `src`. None of those objects carries the omitted directory page.

C13's actual result has the first 16 of 25 paths, including `patching.py` and
`records.py`, with `next_offset=16`. C16 eventually requests that exact same
`tree` operation (path, offset 0, limit 16). Its actual result is identical to
C13's, including candidate binding and entries. No intervening edit invalidated
the earlier page.

Exact anchors in `calls/C16-assistant-reasoning.txt` are useful without duplicating
the full deliberation:

- Line 65 identifies the normal `_make_unit` and `exact_text_for_unit` extraction
  expressions as consistent. This compares their computation, not an observed
  successful end-to-end reopen check.
- Line 165 identifies the previous listing by EVT-0020; line 167 says,
  “Wait, I don't have the tree result content visible right now.” The actual
  input supports that statement.
- Line 171 proposes finding an edit/patch handler; line 216 again identifies
  EVT-0020 and its absent result. The final public reply then requests the listing,
  rather than merely contemplating another retrieval.

I independently checked the C16 wire request against all three saved request
copies for `admission/I0024`, the native text against the template response, both
message bodies inside that native text, and all eight admission artifact hashes
against their recorded identities. The wire SHA-256 is
`129194e1919588a2d2c23a37899a610d4c43fc55eba48d1f25486dc7607e8053`;
the native SHA-256 is
`349b437987dcdc6064785fecf7efd07f05dd2a3e43ba5bc4accb0a649188752e`.
The saved token list and response usage both report 11,774 input tokens, leaving
12,034 under the input ceiling. Presentation is ordinary with no selected bodies
omitted. No new native measurement was performed for this review.

This strengthens the specific retention finding: a known, still-applicable,
small directory page is absent while its activity row remains, and Qwen explicitly
links its renewed acquisition to that absence. The stated reason is not proof of
sole causality. The supplied sources and their imports already provide some useful
paths; C16 also contains repeated speculation. C09 remains contrary evidence:
there the useful outline was present and Qwen still returned to directory reading.
Neither example cancels the other. Host-side retention can be qualified directly;
another Qwen consultation is not needed to establish that these archived facts
can be displayed.

## Existing mechanisms before a new structure

There is no `address_inventory` function or input field in the inspected current
host. Relevant existing mechanisms are:

- `visibility.retained_inventory` and `selection_page`: bounded inventory of
  **designated** source ranges and saved results. Empty here, because navigation
  does not select either. This is not an inventory of everything discovered.
- The resolver's archived `regions` and `parked_source_regions`: exact reusable
  addresses, including ones outside the prompt. They preserve resolvability, not
  an ordinary visible directory/symbol map. `parked_source_regions` is not itself
  displayed and is specifically about retained recovery-source addresses.
- `work_on(..., results=[RES handles])` / `work_on_exact`: existing model-selected
  retention of complete saved results through later operations. A navigation
  result can already be retained this way; `reopen_result` also retains the
  actually returned saved-byte page. These remain historical records, with their
  original identity and binding. No new storage primitive is needed.
- Six recent activity rows and paged history: provide exact recovery handles but
  currently omit the affordable navigation facts needed to avoid another lookup.

Explicit saved-result selection is the durable option already available. It
requires another model decision, wraps serialized results as text, and a group
replacement must intentionally retain any other desired source. It should not be
presented as a cost-free remedy for ordinary navigation. Automatically placing
every navigation receipt into `self.saved` would recreate growth and blur
model-designated evidence with host presentation policy.

## Minimal candidate

First qualify enriching the existing **bounded recent activity projection** with
navigation facts, rather than creating a second persistent discovery store.
For accepted `tree` and `p0_page` rows still in that window, retain the reported
scope, entries, total and continuation coordinate. For outlines retain the symbol
name/signature/range and associated source address once, mechanically joining
the duplicate entry/region descriptions. Do not include source bodies or claim
an outline supplies edit authority.

Deduplicate identical page/binding facts within the window, and do not duplicate
the latest result already shown in feedback. Distinct offsets must remain distinct
pages; `next_offset=null` on page 16 does not prove that page 0 is displayed.
Preserve original operation/RES identity and actual displayed coverage. This
would make the already-referenced outline available at C10 and allow both recent
directory pages to coexist. It leaves the root's repository-scope claim unchanged.

Bound this optional projection by an explicit rendered navigation allowance and
the complete native-input admission gate. Essential feedback, current bindings,
selected evidence and the recovery control path take priority. Under pressure,
reduce the optional navigation projection truthfully to recovery handles/counts;
do not erase selected evidence or mislabel an omitted page as displayed. Select
among optional rows by a declared mechanical recency/order policy, not inferred
task relevance. Establish the numeric allowance in qualification; these bytes do
not justify inventing a universal token budget.

This deliberately does not keep every discovered page forever. A row eventually
leaves the fixed window; existing explicit saved-result selection supplies longer
retention. If later evidence earns longer automatic discovery retention, evaluate
it separately. A persistent union of all visited paths, classes and references
would reinstate the administrative growth problem even if source bodies remained
external.

## Applicability after edits

Keep archived receipts unchanged. A file-outline location/address is usable as
current navigation only while its file fingerprint matches. An edit shifting that
file's lines invalidates the former coordinates; do not silently move or rebind
an old SRC reference. An unrelated-file edit need not invalidate a matching file
outline merely because the global candidate changed; distinguish original
candidate identity from current file applicability.

Directory facts need equally specific scope. Literal path membership can remain
true under the current existing-files-only policy, whereas `p0_page` directory
byte and symbol counts can change after edits. Preserve the observed candidate
and either mechanically establish the displayed facts still hold or label them
historical. Do not present old counts as fresh state. Navigation metadata never
substitutes for exact current source delivery or a version guard.

## Feasibility and behavioral qualification

After the live runtime closes, use existing native rendering and admission
machinery on cloned exact C04–C10 states. Compare unchanged inputs with the
bounded projection; preserve wire/native bytes, tokens, original receipts,
candidate/account/source selection and grammar. Measure the marginal input cost,
verify both directory pages and the C08 outline actually reach intended later
inputs, and round-trip their addresses without granting edit eligibility. A
researcher choosing a retained result for this mechanical trial is not actor
selection evidence.

Exercise long histories with the same recent window, repeated identical pages,
many distinct maximum-sized pages, overlapping outline/search addresses, a changed
file and an unchanged file after another edit. Include crowded states where
feedback must still be delivered, optional navigation cannot fit, and recovery
selection must remain operable. Verify that metadata and rendering cost remain
bounded independently of archive length. Keep search-result retention separate
initially; its overlapping contexts have different size and usefulness questions.

Only a separately frozen, uncoached exposure can test whether this reduces
reacquisition and helps produce useful source acquisition, saved work, actual
verification and submission. C09 is a necessary counterexample in that review:
the actor may still repeat navigation despite seeing a good outline. Any benefit
belongs to the declared presentation policy and must include its added input
cost. Do not change the live run, impose a preferred next file, or claim a complete
root listing establishes task understanding.
