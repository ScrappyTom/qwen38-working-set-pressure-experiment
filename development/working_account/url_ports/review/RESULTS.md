# Uncoached URL-port contribution: stopped before saved work

The fresh attempt under bbaf1c7a returned four complete responses and committed
three acquisitions. No account, edit, check or submission occurred. The final read
could not fit, and its rejection also exceeded the input ceiling. The attempt and
unused allowance are closed without retry or coaching. It does not demonstrate
an improvement in completed work from the account-plus-verification configuration.

| Request | Input | Generated | Request seconds | Observed action |
| --- | ---: | ---: | ---: | --- |
| C01 | 3,413 | 278 | 21.484 | Select broad test and implementation pages |
| C02 | 22,774 | 2,337 | 192.094 | Read tests 766–800 |
| C03 | 23,387 | 7,167 | 492.078 | Read documentation; 39 lines fit |
| C04 | 23,802 | 2,295 | 193.797 | Propose tests 801–900; no operation committed |

Total input processing is 73,376 tokens and generation 12,077 tokens. Four model
requests cost 899.453 seconds (14.991 minutes); first dispatch through recorded
closure is 949.521 seconds (15.825 minutes), excluding runtime startup. Peak
input-plus-generation is 30,554; memory minimum is 391 MiB. No generation reserve
overrun, truncation, GPU failure or cache reuse occurred. The stopped attempt has
no normal task-loop completion metric. The 33.719 seconds of logged processing
cover only the three processed replies, not all failed fourth-reply processing.

The host delivered every accepted result completely to the next actual input.
The selected source remained available, including the implementation settling the
port behavior. Qwen derived the important expected values correctly but repeatedly
reconstructed the logic and reconsidered reading order. It treated page boundaries
as possible file ends and pursued more broad acquisition instead of saving its
test design. The full transcript review preserves the recovered errors and useful
analysis alongside that cost.

The host's final failure is independent evidence: at the actual state, a one-line
page needs 24,025 tokens, and the rejection needs 23,880, 72 above the limit. The
model never receives the instruction to narrow the group. This is not lost source,
an incorrect check, account misuse or a general demonstration of model inability.
It is a capacity boundary in the current presentation/recovery policy.

The stopped candidate is byte-identical to the start. Exact replay verifies 42
native inputs, 336 custody records and 280 source identities, reproduces the
terminal exception, and confirms local runtime closure. The original verifier
re-raised the terminal exception before its final comparisons; its unsuccessful
run is preserved in `verification-original-001.txt`. `verify_stop.py` adds a
review-only check for precisely that recorded terminal exception, then executes
the original final-state/artifact/runtime comparisons. It creates no tool result
and does not count C04 as processed.

Sixteen requests and fifty-seven operations close unused. The separate two-turn
design consultation and offline scripted contribution/correction routes remain
development evidence, not completions of this run. Task, opportunity budget,
checking policy and account capability changed together; no component-level causal
claim is supported.

The immediate development question is whether recovery feedback can use space
currently occupied by recent activity summaries while retaining selected source,
current state and the exact archive. That is a narrow presentation/admission
question earned by this stop, not another instruction for Qwen to count tokens.
No further model exposure belongs to this consumed attempt.
