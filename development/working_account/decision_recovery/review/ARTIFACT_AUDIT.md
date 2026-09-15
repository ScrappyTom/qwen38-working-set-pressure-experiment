# Scripted work and its evidential limits

Directly reviewed both operation sequences, exact saved patch arguments and resulting
diff, actual tests/public outputs, the task contract and governing port/host-info source.
ARTIFACT_CHECK.json verifies byte-identical final candidates and unchanged bytes for
all files except the intended test and documentation additions. SCRIPTED_CONTRIBUTION.diff
contains the actual final difference, not a draft recovered from Qwen's thinking.

Final candidate: 7f779f7404bdee04dd7ab81326cb26347cab639e2cc05d68370cd31e4646b15b.

The added method exercises both public parsers with strings and ASCII bytes. Accepted
cases cover absent/empty port, zero and 65535. Error cases cover 65536, negative and
noninteger ports, plus non-ASCII decimal digits in strings. Construction precedes
the exception context; access to .port triggers the check. Assertions cover exact
exception type, the complete argument tuple and diagnostic string. The range error
and string/bytes representations follow the actual inspected property and host-info
implementation, which remains unchanged.

The final tests and public checks preserve all 72 old tests and pass the 73-test
edited suite. Recorded instrumentation sees every required API/input path. The added
test detects seven declared changes to class, arguments, message, validation timing,
empty/zero/maximum behavior. These are acceptance checks for one researcher-written
method, not seven independent discoveries. The public check runs eight added doctest
examples successfully. Prose accurately qualifies port validation as occurring on
attribute access for an otherwise valid URL; it does not claim all malformed URLs
can be constructed without error.

The correction route first saves WRONG RANGE MESSAGE and receives an accepted failed
tests check with four failures. The saved edit remains. Its next guarded patch restores
the actual message without changing the library; the triggered tests and later public
check pass on their actual successors. The earlier test contribution survives the
switch to documentation and the final candidate matches the complete route exactly.

There is a researcher-account error in that route. The C05 account states, "The failed
test reports the actual message." The actual prior check output has no diagnostic
message: its size-reduction policy removed all traces. The governing implementation
is still selected and contains the real message, and the script supplied it from
the reference. Thus the sequence proves admission, preservation and failure/correction
execution, not learning the correction from the failed result. Do not repair this
sealed account retrospectively or credit its attribution as source-checked truth.
Before reusing the script, correct that account and qualify useful primary diagnostics.

Other scripted accounts are also researcher-authored inputs. Their wording remains
unchanged after feedback unless the next scripted reply revises it. In particular,
the last account still says documentation is a proposal pending a check after the
public pass arrives. The host correctly preserves authorship rather than rewriting
meaning; the actual current check authorizes submission. No account-benefit claim
or model-understanding claim follows from this qualification.

All choices and reference edits were supplied outside model inference. Qwen received
neither this compact group, the corrected coordinate nor the reference contribution
in a task run. The two consultation answers are separate nonexecuting development
evidence. No unfinished private draft was promoted into saved work.
