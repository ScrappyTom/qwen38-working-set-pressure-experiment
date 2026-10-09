# Next coding contribution: configparser write safety

Owner direction, October 9: work on coding, not papers or further reading-
comprehension fixtures. Detailed reports of completed code work remain wanted.
Finish the already-running COMPASS attempt unchanged. Defer the synthetic E2
entry without changing its historical status. This plan precedes implementation.

## Concrete change

Extend the saved, corrected Python configparser library so writing an option name
that begins with the parser's section pattern or contains a configured delimiter
raises a public InvalidWriteError instead of silently producing a different
configuration. Add meaningful regression tests, preserve the earlier multiline-
continuation repair and tests, and document the limited new API behavior.

This is a real standard-library maintenance backport, not novel discovery. Python
3.14 documents InvalidWriteError. Pin evaluator reference material to CPython
v3.14.0, resolved by git ls-remote to ac991beb29b1783316c4016c99468c008568d08a.
Before freezing the task, inspect the exact implementation/tests and reproduce
the behavior through ordinary write/read execution. Do not claim that these two
checks guarantee lossless serialization for every customizable parser setting.

Baseline is the exact previously completed candidate
20c32a7ff719a132b258d292f8e21122cd211d860469c227b9a7cc9b0da4755b from
documentation_followup/run-001/final-candidate.json. Preserve its ten files and
source/license provenance. This is a new job on saved code; no prior passing check
establishes the new requirement. Start with an empty selected group. Do not carry
an invented working account, researcher source selection or reference patch into
the actor's input.

## Implementation and qualification

1. Pin source material and independently reproduce the unsafe writes and correct
   ordinary cases on the saved baseline. Keep evaluator reference code outside
   actor material. Resolve any mismatch in the scoped contract before exposure.
2. Reuse the existing coding host, literal-source editing, exact observations,
   normal navigation/search, optional accounts and current-job presentation.
   Build a thin task adapter, not another host lineage. No probe/fork procedure,
   mandatory source-reading quota, forced eviction or note requirement.
3. Build a public checker that runs the preserved existing suite, independent
   write-safety cases and the actor's new tests against the saved baseline and
   candidate. Distinguish a current failure from expected old-version failures.
   Include defaults and named sections, both parser classes, configured single-
   and multicharacter delimiters, custom section patterns, valueless options,
   and ordinary round trips/formatting. Do not require a particular helper name,
   internal patch shape, exact new test count or unrequested atomic file write.
4. Qualify the checker against ordinary execution, including a real failure and
   its complete next-input diagnostic. A missing exception alone must not count
   as a meaningful regression test: also test sensitivity against a baseline
   with the exception exported but without the write protection. Preserve exact
   observations before rendering. Existing tests cannot be weakened or removed.
5. Qualify one complete scripted implementation/test/check/submission route,
   actual native reply forms and full initial input. Review what each scripted
   input supports. The reference route establishes feasibility, not actor work.
   Test preservation of prior behavior and a failed-check correction. Publish
   qualified preparation before one uncoached run.

## Prospective run

Use the existing medium reasoning, uncapped generation, 56,576 physical context,
23,808 input ceiling and 32,768 prospective generation reserve. One fresh job,
seed 314159, 40 requests and 120 operations across the whole contribution.
These are finite opportunity bounds, not a guarantee of action completion.
Keep the reasoning, transport and selection policy fixed. Ordinary explicit
checks and the existing requested edit/check combination remain available.
No live coaching, hidden retries, silently enlarged allowance or extraction of
private drafts. Wait for COMPASS runtime closure before any GPU preparation.

## Evidence and completion

Inspect every actual prompt, complete response and effect. Judge the actual code,
regression sensitivity, preservation of previous work, consumed current check,
submission and total cost. Review documentation directly; executing examples does
not certify its prose. Keep host validity, supplied information and actor use
separate. Publish a detailed coding report and exact evidence after closure.
An unsuccessful run remains recorded and earns a repair only when inspection
establishes a concrete defect or missing capability. No further synthetic
reading-comprehension run is the default next step.
