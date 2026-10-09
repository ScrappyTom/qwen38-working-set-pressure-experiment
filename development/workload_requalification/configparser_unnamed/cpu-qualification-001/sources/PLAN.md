# Implement opt-in unnamed sections on the saved parser

The owner requests substantive coding rather than papers or further synthetic
reading-comprehension tasks. Start from the exact completed write-safety candidate
0f23fd5116a90cda202f48b5010e4eed6057ce99cea921a9328009b79c9ee3c4. Preserve its
multiline repair, write guards and existing tests/support files. This is a new
feature contribution, not a replay of the completed job.

## Useful implementation scope

Add opt-in unnamed-section support using the established public API names
allow_unnamed_section, UNNAMED_SECTION and UnnamedSectionDisabledError. A headerless
prefix must be a separate section, not defaults. The feature crosses parsing,
programmatic access, mapping and writing. It therefore tests integration with saved
work across several actual implementation paths rather than another isolated guard.

The prospective task will explicitly require reading and updating unnamed options,
multi-source merges, ordinary duplicate/continuation behavior, programmatic sentinel
use, and writing unnamed options before any header so defaults and named sections
remain distinct when read back. Existing InvalidWriteError protection must also
apply to unnamed options. Default-disabled behavior stays compatible.

This is a scoped feature contract, not a claim of byte-for-byte CPython 3.14
compatibility. The already pinned upstream v3.14.0 source/doc/tests are evaluator
references. Its read_dict string conversion and default-first writer deserve
independent probes before being treated as an oracle. Do not silently weaken the
declared contract to make a copied reference pass. New task requirements, including
sentinel mapping and defaults round trips, must be visible to the actor.

## Implementation and qualification

1. Define an exact task and independent public-API cases, including both parser
   classes and preservation. Qualify with a minimal evaluator implementation,
   ordinary execution, the saved baseline and meaningful behavioral faults.
   Preserve unsuccessful preparation attempts. No exact diagnostic wording unless
   explicitly required; no test of private implementation choices.
2. Reuse the coding host plus the qualified recovery_navigation mixin. Start with
   empty selection/account and the saved code; no reference patch or source group
   enters the actor input. Keep medium effort, literal-source/JSON transport and
   explicit later check policy unchanged. No compulsory reading quotas or notes.
3. Add one new regression file. Preserve all previous executable tests, support,
   data and license bytes. Allow only the library, new tests and relevant library
   documentation to change. The checker runs preserved suites, independent feature
   cases and authored tests. Compare authored tests with the original missing-feature
   library but do not mistake missing-API errors for proof of meaningful assertions;
   directly review tests and assess behavioral sensitivity separately.
4. Qualify the actual native forms, complete starting input and a scripted
   acquisition/edit/check/submission route. For each scripted acquisition use actual
   discovery or a named target; reference code is feasibility evidence, never model
   capability. Verify exact serialized restoration and current source authority.
5. Publish qualification before one uncoached run: 40 requests/120 operations,
   no reset, automatic retry, silent extension or live coaching. Read every actual
   input, full response and effect. Stop for a demonstrated apparatus defect rather
   than spending the remaining opportunity on invalid feedback.
6. Replay custody and independently run the saved code through ordinary unittest,
   the declared contract and behavioral sensitivity. Review documentation semantics
   and any executable examples in their stated environment. Export the actual work.
   Report correctness, regressions, actual use of feedback, completion and full cost.

The recovery correction is a declared part of this development configuration.
One successful feature run will not isolate its performance effect, prove account
benefit or establish general autonomous programming capability. The deciding
outcome is a correct saved feature that preserves the earlier contributions.
