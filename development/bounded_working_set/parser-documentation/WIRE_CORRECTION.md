# Prospective request-order correction

The completed documentation session is preserved at **16ce028e**, with its original
implementation c52f26fc. Reproduce its four recorded verifications from the complete
16ce028e checkout; the current prospective verifier expects the new wire evidence.
No consumed prompt, output, operation, source identity, seal or original report
is rewritten. The task and its two unused replies remain closed.

The correction changes only the top-level reply forms' property order in the
completion request. Canonical JSON still identifies the logical request; the
actual wire serialization preserves discussion/operation/check_after, matching
the illustrated form. All nested action schemas, guards, constants, input text,
sampler and reasoning settings remain unchanged. An incomplete or duplicate
property-order declaration stops preparation rather than dropping constraints.

Preparation now saves the exact wire request alongside its canonical logical
request and native input, each with its own identity. Before a completion is sent,
the runner checks its bytes against the prepared wire hash and records them in
custody. A mismatch stops before delivery or sending. The prospective verifier
checks that exact body, logical equivalence and prepared identity as well as the
existing response, native-input and operation evidence. Generic historical
request serialization is unchanged.

The focused command from TESTING.md now passes **45 selected tests**, including
18 contribution-wrapper tests. New checks cover unchanged logical constraints
and native text, preparation's separate wire identity, invalid order rejection,
wire mismatch before sending, and custody of the exact body before the mock
endpoint receives it. These are host tests, not model requests or a full suite.

[wire-qualification-001/RESULTS.json](wire-qualification-001/RESULTS.json) exercises
the implemented serializer with the actual pinned model vocabulary and native
GBNF sampler, using the pinned schema converter. Its corrected grammar is byte
identical to the previously inspected corrected grammar. All six cases meet their
expected outcomes:

| Case | Native result |
|---|---|
| Original illustrated combined reply under the old schema order | Rejected |
| Same reply through the implemented serializer | Accepted through EOS |
| Ordinary reply through the implemented serializer | Accepted through EOS |
| Discussion-only reply | Accepted through EOS |
| Unsupported check name | Rejected |
| Combined edit missing its pre-edit file guard | Rejected |

The script verifies model, DLL and converter identities and records exact case
bytes, grammars and result hashes. It loads vocabulary only; no model context,
decode, server completion or inference call occurs. Its sealed output is separate
from the original probe, including the preserved unsuccessful LLGuidance-backend
attempt. The implemented-wire qualification itself passes on its first execution.
Native loading logs remain local under grammar-review/private-runtime, with their
hashes in WIRE_QUALIFICATION_LOGS.json.

The full evidence commit's whitespace check reports original CRLF output and
whitespace in captured reasoning/diffs. Those exact evidence bytes are preserved;
authored review and changed-code whitespace checks pass. Whitespace diagnostics
do not invalidate the sealed source or justify normalizing model output.

The correction establishes that the offered form is available to the decoder.
It does not establish that Qwen will select it, a speed improvement, or the cause
of all preceding deliberation. The completed model attempt used ordinary edits,
check and submission after reviewer clarification of the host issue. Evaluate
combined use during the next independently useful contribution; do not invent
another edit or spend closed replies merely to obtain a favorable example.
