# Affordable recovery detail is admitted after source reduction

This completes the offline plan published at 82c1aaf6. The closed six-request
continuation remains unchanged. No additional model response or checker execution
was requested, and no performance benefit is claimed.

## Earned change

The actual C06 input contained only 6,115 tokens after the host omitted its large
source bodies. It also omitted both exact addresses from the two-match patch
rejection and the 285-byte account. The archive contained them. Native measurement
established that both could be delivered together in 6,757 tokens. This was a
coupled projection policy defect, not a lack of storage or physical input room.

`RecoveryDetailSession` is an opt-in successor of `ReferenceSession`. It first lets
the existing policy choose its source-body arrangement, then measures complete
feedback and account in that arrangement. If both cannot fit, it tries complete
feedback independently and complete account independently before retaining the
truthful brief/exact-history fallback. Each trial measures the complete proposed
input; no new field quota or model instruction is introduced.

The change retains check scope and actual observation interpretation when restoring
a check receipt. It does not restore hidden source bodies, choose a relevant source,
rewrite an account, change an operation or grant editing authority. The original
historical classes are unchanged. Genuine minimum-capacity failures still stop.
Full account text can itself be cheaper than truncation metadata, so recovery tries
the actual alternatives even if the parent's smallest arrangement failed admission.

The immutable `restored_control_fields` tuple is part of presentation state. Cloning
preserves it. The qualification's checkpoint adapter records it explicitly; future
adapters using this successor must preserve it as well. In ordinary mode the
inherited view is unchanged.

## Qualification and direct review

All 62 selected tests pass in `tests-002.txt`, including six new boundary cases:
bulk omission with full control restoration, independent oversized fields, truthful
minimum failure, a short account cheaper than truncation, cloning/delivery guards,
and preserved check execution/scope. `tests-001.txt` retains the first five-case run.
This is a selected regression run, not a full repository suite.

`qualification-001` starts at the actual pre-C05 checkpoint. Its wire input remains
byte-identical at 23,798 tokens. It applies Qwen's complete public C05 reply; all
operation results and the candidate remain identical to the closed run. The next
input now shows `match_count=2`, both addresses, zero remaining undisplayed matches,
and the complete account, with source bodies still omitted.

| Arrangement | Native input tokens | Meaning |
|---|---:|---|
| Closed live C06 | 6,115 | Both addresses and account text omitted |
| Corrected feedback | 6,757 | Both addresses and complete account delivered |
| Researcher-selected first address | 6,504 | Exact current documentation lines 133-137 displayed |

The address selection demonstrates an available operation, not model selection or
a recommended documentation placement. Both returned addresses resolve. An address
alone still does not authorize editing. Direct review of the resulting source,
account, rejection, verification and visibility fields confirms these distinctions.
The account still says the patch is being proposed: it was authored before rejection
and is not silently rewritten into a successful-work claim.

`verify_detail.py` reproduces both transitions and exact saved views/states using the
recorded native measurements. It verifies eight native inputs, 59 custody records,
357 source identities and runtime closure, without new inference or check execution.
The source remains unchanged throughout. The owned server is closed and its port free.

## Remaining boundary

The repair supplies information that the previous host unnecessarily removed. It
does not establish Qwen's next choice, documentation correctness, reliable completion
or savings against C05's prior lengthy deliberation. The six-request live allowance
is closed; this offline follow-through authorizes no further call. Any later
behavioral attempt needs its own frozen package and realistic finite opportunity.
