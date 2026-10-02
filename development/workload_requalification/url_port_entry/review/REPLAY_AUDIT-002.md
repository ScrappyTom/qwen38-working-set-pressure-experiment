# URL run 002: exact replay and independent accounting

The closed attempt is reproducible from its saved records. The first execution of the committed evaluator-only `verify_run.py --version 002` passed: 20 replies, 30 operations, 94 measured native inputs, 898 custody records, 32 restored checkpoints, and 402 bound source files. It verified the published task/preparation/source bindings, actual wires and saved native counts, request/operation ordering, state and candidate snapshots, complete check observation, and owned runtime closure. No checker, model, or native tokenization operation was rerun. The first-attempt stdout is preserved in `VERIFY-002-001.log`; `VERIFICATION-002.json` records the result and helper identity.

Independent accounting reads the actual endpoint responses, sent wire requests, operation receipts, native count files and custody records directly. `measure_run_002_independent.py` and `METRICS-002-INDEPENDENT.json` preserve that calculation; its first-attempt stdout is `METRICS-002-001.log`. The calculation does not import the host or accept a reported aggregate without recomputing it.

| Quantity | Saved-record result |
| --- | ---: |
| Sent requests / complete responses | 20 / 20 |
| Actual operations | 30 |
| Accepted / rejected operations | 29 / 1 |
| Cumulative sent input tokens | 263,924 |
| Generated tokens, including thinking and final output | 50,169 |
| Model-request seconds | 3,430.280 |
| Response-processing seconds | 131.425 |
| Task-loop seconds | 3,612.266 |
| Peak sent input | 23,801 tokens |
| Peak generated response | 10,678 tokens, C20 |
| Peak sent input plus generation | 27,724 tokens, C10 |
| Native sizing trials, including unsent proposals | 94 |
| Peak sizing trial, including rejected/unsent proposals | 32,390 tokens |

The operation sequence contains three directory requests, thirteen reads, two searches, one `work_on`, nine model-authored accounts, one patch, and one declared host-policy check. Twelve source reads were accepted; one broad read was rejected. No documentation edit or submission occurred. The peak native sizing trial is not a sent input or an admitted state. All twenty complete endpoint responses report normal `stop`, uncached input, and generation within the prospective reserve. Runtime closure records no CUDA failure or context truncation, a 238 MiB minimum GPU margin, owned shutdown, and a free dedicated port.

## Delivery and recovery

Every nonterminal reply's latest outcome appears in the actual next wire input. Earlier account receipts from combined replies also match their archived outcomes. In total, 27 of the 30 operation outcomes reached a subsequent model request; the final three belonged to C20 and have no subsequent request. The source-body comparison separately verifies fifteen acquired source extents in their next actual input, including the three-member C12 selection. This establishes delivery of those exact returned extents, not whole-file inspection or correct interpretation.

The C11 capacity rejection reached C12 completely in a 6,047-token recovery input with no bulk source bodies. Qwen's C12 `work_on` selected three sources, and C13 resumed ordinary presentation at 21,972 tokens. The next search caused another recovery presentation; C14 received its exact search result in 9,815 tokens. C14–C20 then obtained and retained new exact inspection excerpts while the previous designated bulk bodies remained omitted. Recovery presentation therefore must not be counted as absence of all current-source evidence. There were twelve ordinary and eight recovery inputs.

## Final check and termination

C20 saved an account and test patch, then the declared host policy executed the tests check on the actual successor. `CHK-0030` ran to completion; its entire 14,130-byte stdout and empty stderr were preserved and replayed exactly. Direct inspection of that stdout shows the saved suite passing 72 tests and the edited suite passing 73 tests. Normal required-path coverage was complete. The original exact-class injected fault passed the added test, so that fault was not detected; the remaining six injected faults caused test failures. The failed aggregate tests result is distinct from an ordinary suite failure and distinct from the expected failures that demonstrated detection of the other injected faults.

The resulting check report was admitted into a 16,663-token next input, but no C21 existed. The actual terminal disposition is `request_allowance_exhausted`, not operator stop, physical-context exhaustion, or submission. The failed check could not be interpreted or corrected in this attempt because all twenty adaptive model requests had been consumed. Thirty unused recorded operations do not provide another adaptive response. The apparatus's check-opportunity rows explicitly measure action allowance only and cannot establish that correction remained possible after C20.

The task-loop/model difference is 181.986 seconds. Of that, 131.425 seconds is recorded response processing; the remaining 50.561 seconds includes other loop work. The records do not justify attributing either whole interval to storage or checker execution. C20 used 641.406 model-request seconds; the preceding nineteen requests used 2,788.874 seconds. These costs locate work, but do not identify wasted reasoning or isolate its cause.

Exact replay and accounting establish preservation, execution, delivery and closure. They do not establish that the accounts' interpretations are true, that the saved test fully meets the assignment, that documentation was completed, or that more requests would have produced success. Those require the separate direct transcript and artifact review. The original run, preparation and frozen implementation were not changed by this verification.
