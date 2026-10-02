# URL-port run 002 — independent final artifact audit

Closed, read-only review of the actual saved candidate and already-executed observation. No checker, model, native decoder or runtime was invoked for this audit; no frozen source or run record was changed. This is an artifact review, not a full transcript or replay certification.

## Result

The run saved a useful but incomplete regression contribution. Its one new method exercises the required normal API/input categories and detects six of the original seven injected faults. It does **not** assert the exact exception class, and the recorded tests scope fails for that reason. Documentation is unchanged. No public pass or submission exists. The original entry therefore remains incomplete.

The recorded disposition is `request_allowance_exhausted`: 20 requests and 30 operations. The final contribution was saved in C20, followed by its declared tests check. There was no subsequent model request in which to consume that failed observation or correct the artifact. This audit does not infer how a further response would have behaved.

## Exact basis and identities

I read the complete original `development/working_account/url_ports/TASK.txt` and compared it byte-for-byte with the task in the actual C20 wire input. Its SHA-256 is `18f90ff54e3703df94aacfeda94e273631fd569eeaf12c951f4a58021f222346`. All six starting bodies match the original `url_ports/world` bytes. The original SOURCE manifest is bound at `a80f1f80f9228b15d6b2a32513d791eae995ec4c0e93792052ab4ec7ebcc3548` (CPython v3.12.0, commit `0fb18b02c8ad56299d6a2910be0bab8ad601ef24`).

- Starting candidate: `2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd`; starting container SHA-256 `6bdb96b0e4e7409f228dc5f4711f7a12b69e0a1b545a9b0938024db97408e731`.
- Actual final candidate: `83d8704c0a98ca6b201c991c56951d2e95bc060af33523531aa0b7789bf304ef`; final container SHA-256 `b3496da5b500b77ab1320cabbeded89b22e44471719d1e031cd885cbbfe3c9d1`.
- Final test-file SHA-256: `db7cc7f82acdea508adf662c9021c12be3e4ed79b1c4d95d6d5be9e907543088`, 76,252 bytes; original `c8f4d478470cb5b3e9daa653a42d029be19aef842fd9577fd524415ce2f037d1`, 72,867 bytes.
- Closure seal aggregate: `8cabf23f04d79c04b899d74c00ed7d456581287b4256ae84adb3e03535fa82b2`; seal-file SHA-256 `22261c75844433e47dd3f65f71cdc4b40801085bcd3f95e1ee42003e20607645`.

I verified the seal's hash/size bindings for the starting/final candidates, final state, C20 wire, decoded reply, actual public content, all three C20 receipts, combined host result, and all four CHK-0030 files (14 records). I independently recomputed every final file-content fingerprint. This is a targeted binding check, not verification of every sealed run artifact.

## Saved change and preservation

The only candidate change is insertion of `UrlParseTestCase.test_port_boundary_and_errors` before `test_attributes_bad_scheme` at original line 735. I reviewed the entire inserted method and actual patch receipt. Removing exactly that insertion recovers the original test file byte-for-byte. AST comparison preserves all 75 original class methods and adds precisely one method; normal executed suite counts are 72 before and 73 after.

The remaining five files are byte-identical to the original: `Lib/urllib/parse.py`, both package initializer files, `LICENSE`, and `Doc/library/urllib.parse.rst`. In particular, the implementation authority was not changed to satisfy the tests. The documentation remains 33,991 bytes with SHA-256 `052a4d950fa1d5311fe1a59cea668b028a12d7dc37c16603451c34513110fa3d`; none of the requested explanation or new examples was saved.

C20 was a public requested patch, not an extracted private draft. The JSON decoded from `C20-assistant-content.txt` equals `C20-reply.json`. The actual input supplied the unchanged task, current implementation lines 1–350 including the port property, and exact current test lines 527–750 including the insertion anchor. The reply guards name the original candidate and test fingerprint; the patch receipt names the actual successor above. The account was recorded as model-authored before the edit/check. It says documentation and submission remain, and makes no claim that this not-yet-executed test check has passed.

## Requirements assessed against the actual test

| Requirement | Saved artifact and preserved observation |
| --- | --- |
| Both `urlsplit` and `urlparse`; text and ASCII bytes; absent, empty, 0, 65535, 65536, negative and noninteger ports | The loop covers both APIs and both types with explicit values. The normal `observed_paths` execution reports no missing paths and `complete=true`. |
| Non-ASCII decimal digits in text | Arabic-Indic digit one (`\u0661`) is exercised for both APIs with the literal expected cast diagnostic. |
| Accepted results | Explicit assertions expect `None` for absent/empty, 0 and 65535 for the accepted boundaries. The empty-port URLs contain additional path text, but their authority still has an empty port; this does not create a missing coverage category. |
| Validation timing | Construction occurs outside `assertRaises`; only `.port` access is inside it. The recorded eager-validation fault errors during construction and is detected. |
| Complete arguments and diagnostic | Every invalid case compares the complete one-element `.args` tuple to its expected diagnostic. There is no separate `str(exception)` assertion. Those literal expectations agree with the inspected implementation, and the original argument/message faults are detected. This does not supply the missing exact-class assertion. |
| Exact exception class | Missing: `assertRaises(ValueError)` accepts subclasses, and the new method contains no `type(exception) is ValueError` assertion. The recorded subclass fault succeeds. |
| Documentation and checked submission | No documentation addition, no examples/public execution and no submitted result. These obligations remain. |

## Actual execution observation

`C20-operation-03.json` and `observations/CHK-0030/outcome.json` bind the automatically requested tests scope to the actual successor and checker SHA-256 `fea743cb4976dd1de60de15cf1e54c5fdee863466c29196ce0f411c802229740`. It executed, completed, returned code 1 and `passed=false`; this was not an operation rejection or an ordinary application-test failure.

The complete preserved 14,130-byte stdout has SHA-256 `da0b3ef05961dc648baec2a15f9dfda9cf46a7190772c2ca3c749b6ed3f054ce`; stderr is empty. Capture is recorded complete. I read its full structured suites, fault results and diagnostic traces:

- Original ordinary suite: 72 tests, no failures/errors; edited ordinary suite: 73 tests, no failures/errors.
- Added-test normal path execution: one test, successful, every required path covered.
- `error_class` injected run: one test, successful; the subclass mutation was **not detected**.
- `error_arguments`, `error_message`, `empty_port`, `zero_port`, and `maximum_port`: injected runs each fail an assertion, so those faults **are detected**.
- `eager_validation`: injected run errors at parsed-result construction, so that fault **is detected**.

Missing-path lists after those deliberately failing runs reflect early termination, not additional coverage obligations. The original rule is aggregate fault detection after successful normal execution/coverage; the recorded reduced report correctly names only `detect.error_class` as the failed criterion. A tests-scope result would not independently establish documentation accuracy even if it passed.

The preserved observations are sufficient to establish the concrete remaining class defect and incomplete documentation. No additional evaluator execution was necessary. Full-run interpretation, selection quality, cost and next-input delivery are left to the separate transcript/host reviews.
