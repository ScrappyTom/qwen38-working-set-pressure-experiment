# T01: exception documentation saved; planned check not requested

Direct review covers the complete initial model-facing user input, supplied system
and generated operation requirements, all 39,238 thinking characters/344 lines,
the 1,048-character final reply, actual edit result and refreshed source. The
sealed response verifies under implementation c52f26fc: 232 source identities,
38 public files, 27 records, two native inputs and one actual operation replay.
Seal: af644269ca5d9728201641ce15c3cc375aa89b6cf6a13d56fc50bd4215f00e1a.

Qwen has the constructor/default and conditional parsing source, exact exception
and saved regression, the real earlier failed documentation check, and three
documentation regions. It identifies the required exception entry and additional
API explanation early. It correctly recognizes that noncontiguous edits require
separate guarded operations and later edits invalidate checks. It considers a
check after the first edit versus after all edits; either ordering remains allowed.

The final patch adds MultilineContinuationError before ParsingError, accurately
stating the base, source/one-based lineno/exact line, constructor arguments and
errors record. It preserves the existing ParsingError description/version note.
No invented release date, library change or regression modification appears. The
remaining relevant API explanation has not been saved yet. The current candidate
is 4e6cdcc51cdc468d7c8bd1a4937cf11b035034b28fa81a687b44bfb363b1ac79;
the documentation fingerprint is
7f66015fe2f6fa15d14c7a84be92b8a3150970d9a482acc067513150f7bfa26e.

Thinking repeatedly weighs edit ordering, checking, placement, paragraph text,
RST indentation and exact JSON. Some addresses real documentation/edit details;
much rehearses an already available proposal. The old mistaken constructor
assumption does not recur. Speculation about what the checker might validate
exceeds its stated declaration-only documentation guarantee but does not produce
an incorrect edit. These costs do not have isolated causal shares.

Near the end, thinking explicitly constructs a final JSON reply containing
check_after=public, and public discussion says "then check the candidate". The
actual final object omits check_after. The host executes only the requested patch,
records it exactly and performs no inferred check. This is an observable plan/action
mismatch, not evidence the host failed to run a requested check or proof of an
output-grammar cause. The new combined route has not been exercised by Qwen yet.

The full edit receipt and refreshed source fit in the measured next input. They
have not reached another actual model invocation at this review point. Cost is
9,171 generated tokens/514.609 request seconds (8.577 minutes); initial input is
8,823. Minimum sampled free GPU memory is 113 MiB with no observed runtime failure
or truncation. No source acquisition, rejection, pressure or submission occurs.

Next respond to this actual work: report that only the edit executed, identify the
remaining API explanation, and let Qwen continue. Do not rewrite its prose, infer
a missing-information cause from response length or open another design dialogue.
