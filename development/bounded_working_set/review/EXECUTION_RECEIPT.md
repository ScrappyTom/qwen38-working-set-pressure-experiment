# Bounded parser attempt: external reviewer stop

The owner authorized the bounded host and saved-parser contribution with
"Proceed". The attempt used frozen commit **2a58d31**, manifest
`cc3372d8b1dacaa8c344538d83fee6ddd7934d4f0f44534f465638e1ce28501a`,
and preparation-002 plus recovery-001. It started on 2026-09-13 at
06:46:16 UTC. No earlier allowance was reused.

Qwen3.8-27B UD-IQ3_XXS, q4_0 K/V, 56,576 physical context, no MTP,
thinking on/xhigh/uncapped, seed 961207 and cache off remained fixed.
The input ceiling was 23,808; the 32,768 generation reserve was not an output cap.

Eight complete responses produced eight executed actions. C09 started at
07:55:17.671647 UTC. The reviewer interrupted exec session 27236 with Ctrl-C
after repeated reserve-policy failures had been established. The session exited
with code 1. The server and monitor stopped, and port 18124 was verified free.
Minimum sampled free GPU memory was 272 MiB over 20,179 samples under the
owner's existing advisory policy. No CUDA failure or context truncation was
observed. Low GPU margin was not the reason for stopping.

**This was an adaptive reviewer/apparatus stop outside the frozen natural-stop
list.** It is not a natural Qwen failure to terminate, a completed contribution,
or an unchanged experimental stopping policy. The attempt is consumed. Its
unused allowance is not a retry or rescue budget.

The process-group interruption bypassed the runner's normal final seal and
closure events. No synthetic runner event was appended. The original 441-record
hash chain and every existing artifact were left unchanged. The later
[REVIEWER_STOP.json](../run-001/REVIEWER_STOP.json) explicitly records the
external action, limitations and observed closure. The separate sealer checked
unchanging files and absent runtime before adding that receipt and
[RESPONSE_SEAL.json](../run-001/RESPONSE_SEAL.json). Seal SHA256:
`402cd2e034cec912d09aa1380bff7d222a37a613c269d122505d2bff6ef0f961`.

C09 returned no complete endpoint response or action. Its exact generated token
total and elapsed request time are unavailable. The last server counter of 152
generated tokens and file-write times are partial observations, not endpoint usage.
They are excluded from completed-response totals. The 15 requests never started
remain unconsumed within this closed attempt.

[Verification](VERIFICATION.json) checks 208 frozen source identities, 497 sealed
artifacts, all 62 native inputs/admission trials, eight complete raw responses,
eight action/state replays and exact archived payloads. Three private runtime
files were verified locally by hash; their paths/contents remain untracked.
No inference occurred during verification. The public execution console sits
outside the response seal and is published separately. Verification must use
the frozen host, before the prospective capacity corrections.
