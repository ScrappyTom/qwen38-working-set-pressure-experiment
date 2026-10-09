# Qualification envelope is not a changed capture payload

MINT preparation001 qualifies and closes normally. Its first exact replay stops
at _imported_custody's full-payload equality. The preserved original verifier
expects the domain payload from RunLog; the real QualificationLog additionally
records qualification_only=true and completion_sent=false. Neither changes the
imported capture bytes or supplies model evidence. The CPU custody test used a
minimal logger and therefore missed this boundary.

Keep the failed verification, verifier source and sealed preparation unchanged.
The nested supplemental verifier first validates both qualification flags, then
compares the remaining domain payload with the existing exact-body verifier.
The original inventory and hash chain are still validated over original bytes.
It reuses the full native/state/check replay with no model, tokenizer or checker
execution. Its own identity is recorded in a separate SUPPLEMENT result.

The new test uses the actual QualificationLog and checks wrong flags, a false
actor-acquisition claim, and a substituted capture body. This is an evaluator
repair; it does not weaken custody, alter any model input, or require new native
measurements of unchanged input bytes. Run verification keeps its original strict
run-payload contract. Publish this correction before actor exposure.
