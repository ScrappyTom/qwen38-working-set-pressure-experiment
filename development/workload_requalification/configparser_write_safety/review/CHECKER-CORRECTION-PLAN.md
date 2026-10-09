# Correct the checker to match the coding task

Direct review during the first live attempt found one unsupported assertion in
test_public_exception: str(InvalidWriteError('bad key')) must equal exactly
'bad key'. TASK.txt explicitly permits diagnostic wording, requiring only the
offending option name. Public subclass/export requirements do not prescribe this
constructor's message formatting. Existing exception subclasses also customize
their constructors. This is an evaluator mistake, not a demonstrated Qwen defect.

CHECKER-SCOPE-PROBE.json reproduces the problem without model inference. The known
correct protected writer is unchanged; its Error subclass prefixes diagnostics
with 'Invalid write: '. Eleven behavior methods pass, including option-name
diagnostics, and only that exact-message assertion fails. The task is satisfied
by those diagnostic strings. Earlier positive/negative qualifications did not
include an alternative correct implementation of this representation choice.

An orderly operator stop has been requested while C09 is in flight. Finish its
actual reply/effects and seal the attempt; do not alter bound code, coach Qwen,
execute unfinished thinking or claim task completion. Preserve all input, output,
partial artifacts and costs. No recorded check had executed through C08.

After closure and exact replay, remove the unsupported exact-message comparison.
Keep public export/inheritance, actual write-time rejection, offending-name
diagnostics, valid behavior, preservation and regression sensitivity requirements.
Add the alternate correct diagnostic implementation as a positive checker case;
retain unsafe behavior and vacuous tests as negative cases. This changes the
checker contract openly, not historical grades or task requirements.

Qualify and publish a separate package003 before another uncoached coding attempt.
Preserve any actual saved code from C09 in choosing its entry; if there is no code
change, a new empty-selection entry is a repeated exposure to this task and must
carry the stopped attempt's costs in lineage reporting. Do not describe the result
as an independent first exposure. Keep reasoning, transport and selection policy
unchanged. The primary next work remains the library/test contribution, not a new
reading fixture or architecture experiment.
