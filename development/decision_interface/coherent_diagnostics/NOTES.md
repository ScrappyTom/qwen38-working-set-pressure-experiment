# Running implementation and governance notes

- Direct C07 review, not aggregate performance counters, earned this repair. Its
  public explanation associates the first error with a later example's line, exactly
  where the host's excerpt discarded the original location. This does not quantify
  the causal share of 9,664 generated tokens, but the information boundary is unsound
  independently of that estimate. Keep a failure's identity and observation together.
- A counter of one diagnostic blob was mechanically correct but described four
  failed examples poorly. Counts should identify the unit being counted; an aggregate
  stream is not a coherent individual failure record.
- The current projection recognizes the pinned standard doctest format. It does not
  fabricate associations for partial or unknown reports. Explicit unknown state plus
  exact access is preferable to attaching an orphaned tail to an inferred example.
- tests-001 preserves an apparatus mistake: unittest -v implicitly enabled verbose
  output in the nested DocTestRunner. The direct report inspection established this
  before any production-parser change. The fixture now explicitly selects verbose=False,
  matching actual checker execution. The six cases pass in tests-002. The initial
  commentary calling this a parser defect was corrected in the same session.
- Do not call a repaired return value sufficient qualification. Verify immediate
  receipts, standing verification and inspection in the actual complete next input.
  Leave original observations and checker outcomes unchanged.
- qualification-001 preserves an apparatus path error before any new native input
  was measured: per-case custody directories inherited monitoring relative to the
  case, while the owned runtime writes its memory log at the parent. The successor
  passes the parent runtime health function explicitly; qualification-002 is the
  new attempt. No completion or checker execution was sent in the failed attempt.
- qualification-002 reproduces both old inputs byte-for-byte and admits all four
  identified records at 14,324 / 11,999 tokens. The 151 selected tests pass. Native
  preparation admits the actual stopped candidate at 11,666 tokens with its real
  one-failure result and unchanged, inaccurate account. Three earlier corrections
  are inherited work, not an effect attributable to this projection change.
