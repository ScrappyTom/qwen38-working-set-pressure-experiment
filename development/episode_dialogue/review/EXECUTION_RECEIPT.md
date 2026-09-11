# Execution receipt — episode dialogue

The owner endorsed the small separate conversational learning step as the
project's central purpose. Codex made that direction concrete as two development
dialogue turns under [SPEC.md](../SPEC.md), not a new task execution or an unused
pilot allowance. There is no tool executor in this conversation. Every response
is saved in full, including thinking, and each turn closes and seals before
interpretive access. E2 is an adaptive reply to the preserved E1 answer.

The starting repository commit is
`27a93993fb93103ce7ac2cadf12fd592e42e392b`.
The new execution script and dialogue specification were prepared in this
working tree; the execution records pin all 55 actual source/specification
identities. The starting commit alone is therefore not the execution closure.
The source identities remain the same across both calls.

The historical input is L02-012, SHA-256
`01933464b16b463e0d9fbbb3c6acc8d77799dad5ae84bf8c54e689cd78686cbb`.
Its pilot seal remains
`cc3cf5d47d3fca38f9458964503ff9366f893e4e7ee4e5dfaf0bb5abeb9b27df`.
The initial API request preserves both original message bodies exactly as
delimited historical data, inside a new nonexecuting conversational instruction.
The diagnosed L02-012 response, later pilot outcomes and the reviewer's proposed
headings are excluded. Prior action records remain because they were in the
actual historical input. The action-output grammar is removed; all other
sampling/thinking settings are retained except the declared alias and seed.

Qwen3.8-27B UD-IQ3_XXS uses model SHA-256
`c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee`;
llama.cpp b10434 revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a`,
server SHA-256
`5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610`.
Local weights, executable paths and private launch/runtime logs remain ignored.

Both calls use q4_0 K/V, 56,576 physical context, no MTP, thinking on/xhigh,
all generation budgets -1, temperature 1, top-p .95, top-k 20, min-p 0,
repetition 1, frequency/presence penalties 0, seed 42, one slot and no prompt
cache reuse. Full GPU offload, fit off, six threads, batch 256, ubatch 128,
flash attention and no context shift remain fixed. G=32,768 is an admission
reserve, not an output cap; exact native input must not exceed 23,808.
The owner's already accepted 350 MiB reference is advisory, with monitoring.

The template adds its normal xhigh instruction and trims outer message-edge
whitespace. The native input is preserved separately and inspected. E2's API
history retains E1's exact final answer; that final answer also occurs exactly
in its native input. E1 private thinking is not carried into E2. This template
behavior does not alter the content inside the historical-message delimiters.

See [VERIFICATION.json](VERIFICATION.json) for the final per-turn counts, seals,
memory and independently recounted native inputs. Verification is offline;
it neither requests another completion nor certifies direct reading. The
separate transcript audit records that reading.

| Turn | Native input | Generated tokens | Model-request seconds | Minimum free GPU MiB |
|---|---:|---:|---:|---:|
| E1 | 18,173 | 12,756 | 791.391 | 339 |
| E2 | 22,674 | 7,297 | 487.281 | 339 |

Total: 40,847 input tokens, 20,053 generated tokens and 1,278.672 request seconds
(21.31 minutes). These are consultation costs, not task completion costs. Both
finish with `stop`, zero cached prompt tokens, no executed action and no mutation.
E1 leaves 25,647 physical tokens after generation; E2 leaves 26,605. Neither
exceeds the planning reserve or physical capacity. E1 has 3,855 memory samples
and a .224-second maximum gap; E2 has 2,385 samples and a .871-second maximum gap.
These completed workloads do not qualify every larger workload.

Each turn seals 11 public inventory files plus the seal, with 11 chained records.
E1 seal: `f1b2a215811e5102298423fbf4cdc31129ba17dd6419317f6f563565cfcfc62a`.
E2 seal: `78b2042ea0beabaa14b6805214c6b6ecf192de3224fccfa1e2b4e5ca54e85194`.
Both full inventories, chains, 55 source identities, private runtime hashes,
actual launch settings, native/CLI token counts, raw output fields, nonexecution
and closed runtime decisions verified through
[verify_episode_dialogue.py](../../../scripts/verify_episode_dialogue.py).

Before exposure, offline assertions checked exact historical input inclusion,
uncapped request settings, absence of the action channel and rejection of E2
without a sealed E1. E2 preflight checked the exact first answer and unchanged
source identities. Separate framing qualification checks all 24 archived inputs
and three negative cases without inference. No full repository test suite was
run or claimed; no runtime, executor or historical fixture was changed.
