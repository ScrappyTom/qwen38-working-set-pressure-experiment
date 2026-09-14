# Saved work and rejected proposal

All assessments below occur after the model attempt is sealed. The original library,
tests, documentation, proposals and results are preserved. No reviewer-applied repair
or check is returned to Qwen, substituted for its saved artifact or counted as another
successful trajectory.

## Actual saved artifact

The final candidate is
`4220f1e3715a2da02d582c805fe69299b228734c00a019fc0f4ad4461440ec4b`.
Only Lib/test/test_configparser.py changes; its final SHA256 is
`17bda15c3993562c3b6a24d6ba45525d2da8a56ef0f1dae8cf5dcbc810612e0c`.
ACTUAL.patch contains the exact addition. Earlier test methods, library source and
documentation are unchanged. The fourteen added methods obtain real lookup errors,
exercise Basic and same-section Extended copying/pickling, and include raw and
successful-lookup cases. This is saved partial work, not merely a discarded sketch.

The frozen public checker, run independently on that exact candidate, fails:

| Assessment | Result |
|---|---|
| Previously saved suite | 359 tests, five skips, no failures/errors |
| Edited suite | 373 tests, five skips, two failures, no errors |
| Backport contract | Eight passing tests |
| Previous work preservation | Pass |
| Required new documentation | Absent |
| Required lookup/transport paths | Incomplete |

POST_RUN_CHECK.json preserves the actual bounded checker result. Because that result
clips failure examples, diagnose_saved_failures.py separately runs the two failing
saved methods with the same frozen harness and preserves their full traces in
SAVED_FAILURE_DETAILS.json. It changes neither the test source nor experimental score.

1. test_basic_missing_option expects a message saying the reference is not a section
   name. Actual Error formatting returns the Bad value substitution message naming
   the missing interpolation key and raw value. The constructor and formatter that
   establish this were visible through C03 but absent from C06.
2. test_extended_cross_section_missing expects reference `nope`. The actual reference
   is `other:nope`, matching the full expression passed by ExtendedInterpolation.

There are additional coverage omissions visible in the exact source: no argument-tuple
assertions; isinstance assertions rather than exact class checks; no transport of
the cross-section error; and no diagnostic assertion on restored Extended exceptions.
These are direct contract comparisons, not further executed suite failures.

Interpret the instrumentation precisely. Its empty Extended transport list filters
for cross-section errors; the artifact does contain successful same-section Extended
copy/deepcopy/pickle tests. Its empty raw_bypass list requires the raw call to use the
same parser instance that raised an observed exception. The new standalone raw=True
tests exist and pass, as do successful-lookup tests. Do not describe raw behavior as
untested merely because that instrumentation association is absent.

All four restoration-fault runs fail, but the unmutated suite already fails twice.
Their additional traces include restoration-specific failures; the aggregate fail
flags alone are not four clean independent detections. The incomplete artifact is
not rescued by a mutation failure count. No new documentation exists to execute or
assess for accuracy.

## Exact C02 proposal, never saved in the model run

assess_rejected.py reconstructs the actual pre-C02 candidate, verifies both version
guards and the unique old fragment, and applies the exact rejected proposal only in
an isolated reviewer candidate. REJECTED_C02_ASSESSMENT.json records the actual public
check. This proposal produces candidate
`ec06aa2592907d5274a349c22904c7b60b7e42949058558e5292ec0d3282887e`.

Its twelve added methods yield 371 suite tests with five skips and no failures/errors.
The observed Basic and cross-section Extended paths include shallow copy, deep copy,
pickle protocols 0-5, raw bypass and successful resolution. Argument tuples, exact
types and message state are asserted. Each of the four restoration mutants produces
new assertion failures against this passing unmutated suite. Prior work remains
unchanged. The whole contribution still fails because it adds no documentation.

The proposal checks diagnostic text through the exception's message field, not str.
The actual base formatter was visible in C02. Do not attribute an unperformed str
assertion to this proposal or treat passing checks as exhaustive correctness proof.

The separate native capacity probe confirms this same proposal would fit at C05
after the selection changed. It was not accepted in C02, retrieved in later model
inputs, executed by the actor, or checked by the actor. The later accepted C06 tests
are a newly generated, different and weaker artifact. This within-run contrast makes
turn-specific support worth investigating, but it does not control for generation,
selection, remaining allowance or repeated exposure.
