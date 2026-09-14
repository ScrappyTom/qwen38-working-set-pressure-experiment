# Grouped recovery of pending work

The development host now lets `work_on` select exact saved action handles (EVT)
beside source and saved result handles (RES). The actual rejected-proposal route
reaches checked submission offline within the original four remaining requests.
No Qwen completion or consultation was sent. This establishes a usable host route,
not that Qwen will select it or finish more reliably.

## What changed and why

The preceding qualification exposed a mismatch between intention and public
capability: EVT-0071 held the complete rejected test proposal, but `work_on.results`
permitted only RES handles. Recovering supporting source and that proposal required
two requests. The existing payload reader and group executor already handled both
record types. The change is one accepted-handle pattern and its visible explanation
in `working_view.py`; the argument name remains `results` for compatibility.

The reference explicitly distinguishes saved result bytes from saved action bytes.
Selected records remain complete originals. Source pages are host-sized. Selecting
a proposal does not execute it, make its guards current, establish current source
inspection, or prove success. The existing edit guards, source-delivery gate,
transactional admission, checker applicability and submission gate remain intact.
No storage, selection algorithm, inference policy or budget was changed.

This follows the completed consultation's useful finding that supplied supporting
source resolves the diagnostic question. It does not adopt Qwen's mistaken argument
for batch editing. The earned limitation here was reproduced in the actual public
contract and existing offline route, not inferred from a preference for a new tool.

## Actual rejected state through completed contribution

The historical prefix is not replayed under changed instructions. The qualification
loads the exact previous working-view source from commit
`99052976e2a40ee8aa29247a5bd6f8587007b972`, verifies its recorded hash and all other
bound source files, and replays C01-C04 to the exact saved rejected state. It then
restores the current contract for these prospective, researcher-scripted steps:

| Request | Actual operation | Next complete input | Requests used / 8 | Operations used / 12 |
|---|---|---:|---:|---:|
| Q1 | Select ten source regions and complete EVT-0071 together | 12,624 | 5 | 5 |
| Q2 | Apply the unchanged recovered test proposal | 15,376 | 6 | 6 |
| Q3 | Add the same reference documentation; check the actual successor | 17,882 | 7 | 8 |
| Q4 | Submit that checked current candidate | 15,655 | 8 | 9 |

All five operations are accepted. Before Q1, the input is 22,832 tokens. The
intermediate state between documentation edit and check is 15,839. Six distinct
inputs are measured using the native template/tokenizer; every one is below the
unchanged 23,808-token ceiling. The first state's user message and model settings
are identical to the preceding qualification; the revised reference adds 80 input
tokens there. These are actual input costs, not a measured generation saving.

The selected group is the same researcher-chosen ten regions used previously,
including Error's formatter, the derived exceptions and interpolation paths,
constructor/default/get behavior, test imports and exact tail anchor, and relevant
documentation. The complete 10,706-byte proposal is visibly returned at offset zero
with no continuation offset. Its SHA-256 remains
`b1248585387ec73d80f95a9784e52da579e1414a30bbb721a69d03331712621b`.
The base-class source and proposal remain visible through saving, checking and
closure. Actual patch/check receipts enter the following inputs. The original
rejection and all earlier history remain unchanged.

Direct inspection of the returned proposal, saved source, documentation edit,
checker output and submission binding agrees with the replay. The proposal tests
real Basic and Extended interpolation failures, including cross-section references;
checks concrete args, attributes, message and string diagnostics; exercises copying,
deepcopy and every available pickle protocol; and checks raw retrieval and successful
resolution on the affected parser. The doc examples distinguish raw retrieval from
repairing a missing setting. They are the unchanged examples already executed in
the preceding thirteen-example documentation assessment.

The actual public checker runs 377 edited tests with five skips and no failures
or errors; the 359 saved tests and eight backport contract cases also pass. All
eighteen added test methods pass and detect the four restoration faults. The
checker still requires direct documentation review; its mechanical pass is not a
general semantic guarantee. The complete final candidate is byte-identical to
the preceding qualified artifact:
`5b7b3b06f55935d950317fedce9add1d481c56e15d29158e2a38ddeda369131d`.
Only tests and documentation change; the saved library and earlier work survive.

Previously, four requests and five operations ended at a passing check with no
request for submission. Here the same counts include submission because source
selection and proposal recovery share one request. No original live trajectory is
rescued or relabeled. The old run remains closed with its original outcome.

## Qualification and limits

- **78 selected host tests pass:** 69 operation, eligibility, wrapper and runner
  checks, plus nine capacity/page-layout regressions. Six new sequence tests cover
  mixed records, exact recovery without replay, missing current source, stale
  candidate/file guards, unsuccessful group admission, release and invalid handles.
  This is not a full repository suite.
- **Ten native grammar cases pass.** The actual wire schema admits EVT and mixed
  EVT/RES forms through EOS; the old schema rejects EVT. RES-only and empty handle
  selections remain legal. Unsupported prefixes, short handles, missing arguments
  and seventeen handles reject. This loads the pinned vocabulary and native grammar
  sampler only: no model context, decode or inference.
- **Exact replay passes:** six native inputs, 61 custody records, 272 source
  identities, all scripted operations, current check, final candidate and submitted
  state. The evidence inventory and private runtime custody verify. The native
  grammar evidence has 32 public artifacts and its own verified inventory.
- Runtime settings remain q4 KV, 56,576 physical context, no MTP, medium thinking
  and uncapped generation settings. Tokenization qualification sends no generation.
  The monitored server closes normally and its dedicated port is free. Minimum
  sampled GPU memory is 306 MiB under the existing advisory-margin policy.

The result supports this contract extension as the development baseline. A record
too large to coexist with the requested source still produces a truthful rejection;
exact grouping is not a guarantee that every requested combination fits. Neither
automatic relevance selection nor reliable action completion has been established.
The prior task's stale static provenance sentence is preserved in the reused state;
this narrow qualification does not test or change narrative interpretation.

The next useful model evaluation is a separately prepared uncoached contribution
using the revised contract. Observe whether Qwen actually retains pending work with
the evidence needed to act, preserves earlier correct work, and reaches current
checked submission. No further vocabulary dialogue or architecture change is earned
by this offline success. All prior task and consultation budgets remain closed.

## Reproduction

From the repository in PowerShell:

```powershell
$env:PYTHONPATH='src;tests;scripts;development/evidence_assembly'
py -3.12 -B -X utf8 -m unittest test_working_action_groups test_working_evidence test_working_session test_working_boundaries test_contribution_reply test_uncoached_contribution
py -3.12 -B -X utf8 -m unittest test_working_capacity test_page_layout_capacity
py -3.12 -B -X utf8 development/evidence_assembly/grouped-actions/qualify.py verify
```

The last command replays recorded native counts and actual host/check execution;
it sends no endpoint requests. Historical source blobs must remain available in git.
Fresh native qualification uses `qualify.py qualify --folder <new-folder>` and
`native.py --folder <new-folder>`, each with an exclusive new folder and local pinned
runtime. Existing output folders and failures are never overwritten.

Read [the frozen scope](SPEC.md), [route measurements](qualification-001/QUALIFICATION.json),
[exact replay](VERIFICATION-qualification-001.json), [native cases](native-001/RESULTS.json)
and [native inventory verification](NATIVE_VERIFICATION.json).
