# Closed independent artifact audit: URL continuation run-001

The continuation saved the class-identity correction, added accurate port-access documentation, consumed the actual public check, and submitted its checked successor. Direct inspection finds no material incorrect claim in the final port explanation or executable examples, no library modification, and no loss of preexisting tests or documentation. This is a completed uncoached continuation of saved failed work, not a fresh original-entry success within the old opportunity budget.

## Scope and evidence boundary

This audit reads the original assignment and authority source, the original and actual starting/final candidate bodies, all C21–C32 final replies and operation receipts, relevant actual wire inputs, the complete C30 reasoning, and preserved CHK-0030/0034/0046 observations. It checks source and artifact meaning beyond an accepted submission or checker pass. Root separately reviewed all complete responses.

No candidate import, checker execution, model request, native call, or frozen-source edit was performed for this audit. Static AST comparison and byte comparisons use saved content only. Thirty-four selected run files were checked against their sealed sizes and SHA256 values, including candidate/state files, the relevant wires/replies/receipts, and the four capture files for each observation. This selected verification is not an independent verification of every sealed source or custody record. The separately executed unchanged replay helper reports `replayed_exactly` in `VERIFICATION-001.json` without new checker execution, inference, or tokenization.

The executed revision is `d71e9b98`. `run-001/RESPONSE_SEAL.json` is SHA256 `b07393cd45182f1427645006fa137f6154064f80653dfaa81bf0fdffea3e26ab`; its aggregate is `f943be2add1af3b6029d07745aef84f8dfbc89fd8f34853e11c56a5f98dd7ab7`. Closure is `checked_submission`: 12 new requests and 17 new operations, cumulative 32 requests and 47 operations, retaining the inherited 20/30 under prospective limits 36/60. The original opportunity-exhausted attempt is unchanged.

## Original assignment and actual starting point

Authority is the unchanged saved CPython v3.12.0 source, commit `0fb18b02c8ad56299d6a2910be0bab8ad601ef24`. Original `development/working_account/url_ports/TASK.txt` is SHA256 `18f90ff54e3703df94aacfeda94e273631fd569eeaf12c951f4a58021f222346`; `SOURCE.json` is `a80f1f80f9228b15d6b2a32513d791eae995ec4c0e93792052ab4ec7ebcc3548`. Original candidate identity is `2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd`.

The assignment requires both public functions and text/ASCII-byte URL paths for absent, empty, zero, maximum, too-large, negative and noninteger ports; non-ASCII decimal digits for text; exact error class, full arguments and diagnostic text; validation timing; preservation; and focused executable documentation. The implementation is authoritative and must not change. Tests and public checks are declared edit triggers; only the current public pass authorizes submission. Prose requires direct review.

Continuation entry candidate `83d8704c0a98ca6b201c991c56951d2e95bc060af33523531aa0b7789bf304ef` retains the previously authored regression and failed tests observation CHK-0030. The initial actual C21 input supplies that complete failure report and current source: implementation lines 1–350, test lines 527–824, and documentation lines 125–145. The failed fault-detection result concerns error-class identity, not a normal-suite failure. No reference correction or private draft was supplied in the continuation.

## Actual test correction and contract

C21 proposed a correction but its exact old text used a literal Arabic character where the displayed Python source used the backslash-u spelling. The `old_not_found` rejection is byte-correct, preserves the candidate, and triggers no check. That rejected proposal is not saved work.

C22 uses the actual source spelling and adds exactly seven `self.assertIs(type(ctx.exception), ValueError)` statements to the existing method. The loop executes them for both `urlsplit` and `urlparse`: four text-invalid cases, including non-ASCII decimal digits, and three byte-invalid cases. Successor identity is `07f14bb526d178ba556aff49d52ea553b6d2111685cf167737994a5571b8e70e`.

Direct inspection confirms:

- Both functions exercise text and ASCII-byte absence, empty port, 0 and 65535 with exact accepted values `None`, `None`, `0` and `65535`.
- Invalid 65536, negative and noninteger results are constructed outside `assertRaises`; accessing `.port` occurs inside it. Non-ASCII decimal digits are covered for both text functions. This tests the assigned distinction between construction and port access.
- Every invalid branch asserts the exact builtin exception class and complete one-element argument tuple. The strings distinguish range failure from conversion failure and preserve text/byte representations.
- There is **no separate `str(exception)` assertion**. Exact builtin `ValueError` identity together with its single exact string argument determines that exception's diagnostic text; the text is thereby established through these assertions, not independently compared by `str`. Neither a public pass nor detection of the message mutation should be described as an explicit string assertion that the artifact lacks.

The actual tests check CHK-0034 passes on that successor. The preserved output shows 72 saved-suite tests, 73 edited-suite tests, successful normal required paths, and detection of all seven original faults. Each injected-fault trial executes at least one added test and does not succeed; its early-stop path incompleteness is not an additional required coverage failure. This matches the original aggregate acceptance rather than adding per-fault path obligations.

## Final documentation and preservation

C26, C27 and C29 proposals were rejected because the old text occurred twice. No such proposal changed documentation or ran an automatic check. The inaccurate absent/empty and first-access wording in an early unsaved proposal is not a final artifact defect. C30 obtains the previously unseen second occurrence's surrounding source. C31 then uses a unique anchor extending through the first named-tuple sentence and inserts 38 lines at final documentation lines 136–173.

The saved addition accurately explains the assigned port spelling/range behavior: empty yields `None`; valid nonempty ASCII decimal ports span 0–65535; invalid spelling and range raise `ValueError` on access. It contains no first-access-only claim. Its deferred-validation statement is scoped to port problems under discussion. It does not supersede the immediately adjacent preserved unmatched-bracket and NFKC construction warnings. Interpreting it as a universal promise about arbitrary malformed URLs would extend its stated subject.

The self-contained examples import both functions, use `>>>` prompts, include genuine traceback headers and exact error text, show both valid boundaries, absent and empty `None`, and invalid range/spelling behavior. `urlparse` is included through the too-large-port example; `urlsplit` supplies the other displayed examples. The task does not require repeating every tested API/input combination in the documentation. Byte and non-ASCII coverage remain in the regression, and the prose explicitly identifies ASCII digits. The inline property examples do not independently isolate construction timing; that distinction is supported by the inspected implementation and actual regression structure as well as the explanation.

Existing documentation remains byte-exact around the addition: the first port paragraph stays at lines 133–135; its bracket and NFKC warnings move to 175–176 and 178–181; the second port paragraph moves from 319–321 to 357–359. The second copy is not silently edited or removed.

The final test file differs from the original only by the 81-line insertion at 735–815. Static comparison preserves all 75 original function/method bodies and adds only `UrlParseTestCase.test_port_boundary_and_errors`. The final documentation differs only by the 38-line insertion. Removing each insertion restores its original file bytes exactly. The four other final files, including `Lib/urllib/parse.py`, are byte-identical to the original world. The prior saved regression also remains intact except for the seven class-identity additions.

Final candidate is `f0fe4cd991966428a69696729ac35eec6446b68f9d90b1dc6e26840ca7b75863`. Its six bodies are:

| File | Bytes | SHA256 |
|---|---:|---|
| `Doc/library/urllib.parse.rst` | 35631 | `aafb0ef3dec71aeb335f6d73601302b024bae9237fc1d251c7a4760cb6ff702e` |
| `Lib/test/test_urlparse.py` | 76665 | `3f77112ec7b1c71b9d5e5c6b389ea74c21aed51e7a5cccc34a4f70c55c2b3ae2` |
| `Lib/urllib/parse.py` | 44829 | `2582309acd08b572a7b80b22c2d976cdc42be417503a12afce2d129498456ae8` |
| `Lib/urllib/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `Lib/test/__init__.py` | 47 | `836cdb388117cf81e78d9fa2a141cca1b14b0179733322e710067749a1b16fe9` |
| `LICENSE` | 13936 | `3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf` |

## Actual observation and closure

C31's accepted documentation edit triggers public CHK-0046 on the final candidate. Checker definition SHA256 is `35678aad223ca8e45b470af7dc965e138b2cd7fb63881c40d6381460a76b0aa6`. The complete captured stdout is 15935 bytes, SHA256 `6a3eb7c897adfc92107fae0241dbfc96d89c3bd8804ba757126de0c1598c58f7`; stderr is empty. It reports passing saved/edited suites, normal required paths, all seven original fault detections, preserved existing work/documentation, and nine new executable examples with zero failures. The report explicitly leaves prose for direct review.

C32 receives that applicable public result and submits the same final candidate in EVT-0047. Closure therefore rests on an actual current check, not the inherited failed observation, an account's assertion, or an unexecuted private proposal. These checks and direct artifact inspection support this bounded contribution; they do not prove exhaustive parser correctness.

## Remaining interpretation and process limits

The current account remains model-authored EVT-0040. Its planned unique anchor was rejected, and its pending documentation/check/submission language was not revised after completion. This is stale working understanding, not a host verification claim. Current artifacts, observations and submission correctly record the completed work; account usefulness or general semantic accuracy is not established by its persistence.

C30's complete reasoning questions whether a narrow returned region reference may authorize an edit when the matching current bytes are already visible inside the broader selected source. The actual first occurrence was covered in the delivered 125–260 range; the reference alone was address-only. `DecisionSession` checks current version and complete visible range containment, not equality of the displayed and returned region identities. No narrow-reference edit was attempted or rejected here. The ambiguous-anchor rejections are correct and must not select an occurrence for the actor. Explicitly relating a returned address to already visible coverage is a bounded presentation question earned by this evidence, not an established resolver defect or a proven explanation of all response cost.

This run demonstrates preservation and correction of saved failed work, meaningful tests, documentation, actual verification and uncoached closure with explicitly added opportunity. It does not establish fresh original-budget completion, account benefit, an isolated efficiency improvement, or a new context-pressure recovery result. No further execution is needed for this artifact audit.

Principal evidence: original `TASK.txt`, `SOURCE.json` and `world` bodies; continuation `run-001/starting-candidate.json`, `starting-state.json`, `final-candidate.json`, `final-state.json`, `RESPONSE_SEAL.json`; `calls/C21-*`, `C22-*`, `C26-*`, `C27-*`, `C29-*`, `C30-*`, `C31-*`, `C32-*`; exact `observations/CHK-0030`, `CHK-0034`, `CHK-0046`; and `review/VERIFICATION-001.json`. Source-eligibility inspection uses `src/working_set_exp/feedback_session.py::resolve_region` and `src/working_set_exp/decision_session.py`'s delivered-range containment guard.
