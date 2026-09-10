# Execution receipt — initial interface consultation

Complete: 16 responses received, all with normal `stop`, eight ordinary actions
accepted and replayed, and eight nonexecuting diagnostics. The owned server
and monitor stopped, and the dedicated port is free. Mechanical verification
is in [VERIFICATION.json](VERIFICATION.json); the separate
[direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md) certifies direct reading.

## Scope and identities

One development attempt uses the 16 exact requests in
[the prepared schedule](package/SCHEDULE.json): four states, two seeds, and
separate ordinary-action and diagnostic modes. All eight ordinary actions
precede all eight diagnostics. Each call starts with a fresh two-message
conversation and independently reconstructed actual tool state. There are no
retries, continuations, alternate interfaces, or hidden grading in this run.

The prepared package SHA-256 is
`4f67184164d225f3a1bee1b7c930782dfcb5479317b066e06d77b807264e08cd`.
The first chained record contains the exact launch settings and source hashes
for the runner and every Python module under `src`. The runner's SHA-256 is
`872021262b389a3176775930848d5be31458ec829af5797dda3a3b3d7ef83a0a`.
These identities cover the uncommitted development implementation; the prior
repository base is `970f411851e74e93210c956ba4e0ec6e8b0a29ee`.

| Configuration | Effective choice |
|---|---|
| Actor | Qwen3.8-27B UD-IQ3_XXS |
| Model SHA-256 | `c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee` |
| Runtime | llama.cpp b10434, revision `7e4c0a96880dae4fc4268ad441f8a6446bd5460a` |
| Server SHA-256 | `5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610` |
| Context and KV | 32,768 tokens; q8_0 K and V; one slot |
| Offload | All layers, fitting off; flash attention on; batch 256, microbatch 128; six threads |
| MTP | Disabled; runtime reports no speculative implementation |
| Reasoning | Native embedded template, thinking on, xhigh, uncapped |
| Output controls | Server and request limits -1; no context shifting |
| Sampler | Temperature 1, top-p .95, top-k 20, min-p 0; presence/frequency penalties 0, repeat penalty 1 |
| Seeds | 42 and 314159, as scheduled |
| History | No previous responses or private reasoning supplied; prompt cache disabled |
| Transport | Nonstreaming; existing 14,400-second timeout and 16 MiB response bound |

The private local runtime directory preserves the literal launch command and
raw server logs, including machine-specific paths. Their hashes enter the
response seal; the directory is ignored by Git. The portable chained launch
redacts only the executable and model paths. The model-profile repository and
local handoff are reference material and were not modified.

## Native admission and execution

All 16 requests were rendered with the running native `/apply-template` and
counted with `/tokenize` before the first completion. The largest input is
18,732 tokens, leaving 14,036 physical tokens. The fixed development admission
requirement is 8,192 free generation tokens; it neither caps output nor defines
the future comparison's generation reserve.

The runtime reports 66/66 layers offloaded, a 9,685.21 MiB CUDA model buffer,
and a 1,088 MiB q8 KV buffer. Its speculative-decoding message explicitly says
that no implementations are specified; the adjacent generic checkpoint message
does not establish that MTP is active.

Each raw endpoint response is saved and chained before parsing. The saved
reasoning and final text are extracted without edits. Native preflight prompt
counts must equal actual endpoint usage before any action is executed. An
ordinary response is parsed with the existing strict action parser and executed
once only if it finishes normally with nonempty final content. The host saves
the actual result and complete candidate/session state before and after.
Diagnostics execute nothing. No next invocation is offered to an ordinary
action; this is a state consultation, not an unfinished coding trajectory.

## Completed verification and accounting

The run opened at 2026-09-10 04:28:56.162611 UTC and closed at
06:30:15.672010 UTC. It spans September 9–10 in the owner's America/Denver
timezone. No response was retried or replaced. All eight actions were accepted;
the baseline check in call 1 correctly reports failure on the unrepaired source.
That checker outcome is distinct from protocol or execution failure.

The response seal is
`9968ae5b5cba85448364323e717b26390f8f6c5ab8cb15a45a1e8c4a2edde959`.
Its 178 covered files and all 66 chained records verify. All private-runtime
hashes verify locally. The eight tool replays reproduce exact results and
candidate/session states; two independent offline host probes also reproduce.
Every repeated-seed prompt is byte-identical within its state/mode. Every
native input count matches actual endpoint usage, and all cached-token counts
are zero. A post-shutdown check finds no llama-server process and a free port.

| Mode | Input tokens | Endpoint output tokens | Retokenized thinking text | Retokenized final text | Invocation seconds |
|---|---:|---:|---:|---:|---:|
| Eight ordinary actions | 50,862 | 43,520 | 43,051 | 442 | 2,367.892 |
| Eight diagnostics | 50,704 | 90,274 | 77,497 | 12,753 | 4,900.437 |
| Total | 101,566 | 133,794 | 120,548 | 13,195 | 7,268.329 |

[OUTPUT_TEXT_TOKEN_COUNTS.json](OUTPUT_TEXT_TOKEN_COUNTS.json) records offline
retokenization after server shutdown, with zero additional model completions.
It independently reproduces all 16 native input counts. The b10434 tokenizer's
SHA-256 is `d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c`.
The endpoint reports combined generated output, not separate reasoning/final
token IDs. Retokenized text counts are therefore labeled separately; their
51-token aggregate residual is not asserted to be purely control-token
overhead, because generated segmentation and field boundaries can differ.

| Call | State | Mode | Seed | Input tokens | Output tokens | Seconds |
|---:|---|---|---:|---:|---:|---:|
| 1 | Edit preconditions | Action | 42 | 1,600 | 2,646 | 133.8 |
| 2 | Old check | Action | 42 | 2,884 | 554 | 33.6 |
| 3 | History and partial read | Action | 42 | 2,215 | 9,866 | 507.9 |
| 4 | Crowded external source | Action | 42 | 18,732 | 4,973 | 321.6 |
| 5 | Edit preconditions | Action | 314159 | 1,600 | 9,183 | 469.0 |
| 6 | Old check | Action | 314159 | 2,884 | 885 | 50.4 |
| 7 | History and partial read | Action | 314159 | 2,215 | 13,346 | 693.9 |
| 8 | Crowded external source | Action | 314159 | 18,732 | 2,067 | 157.6 |
| 9 | Edit preconditions | Diagnostic | 42 | 1,688 | 7,776 | 394.3 |
| 10 | Old check | Diagnostic | 42 | 2,825 | 6,088 | 312.4 |
| 11 | History and partial read | Diagnostic | 42 | 2,155 | 15,363 | 799.8 |
| 12 | Crowded external source | Diagnostic | 42 | 18,684 | 13,502 | 819.0 |
| 13 | Edit preconditions | Diagnostic | 314159 | 1,688 | 8,748 | 445.1 |
| 14 | Old check | Diagnostic | 314159 | 2,825 | 12,890 | 671.3 |
| 15 | History and partial read | Diagnostic | 314159 | 2,155 | 12,715 | 657.3 |
| 16 | Crowded external source | Diagnostic | 314159 | 18,684 | 13,192 | 801.2 |

The largest input plus output is 32,186 tokens, leaving 582 of the physical
context. The second crowded diagnostic leaves 892. All release records report
`truncated = 0`; no CUDA/OOM error or context shift is recorded. Whole-device
free GPU memory ranges from 316 to 563 MiB over 14,248 samples, so the profile's
350 MiB reserve is not qualified by this workload. No automatic q4 switch
occurred. Timing and whole-device memory include concurrent desktop activity
and are descriptive, not an isolated runtime benchmark.

With Python 3.12 and `src` on `PYTHONPATH`, reproduce the custody/replay check
into a new output path:

```powershell
py -3.12 -B -X utf8 scripts/verify_interface_consultation.py --package development/qwen_interface_consultation/package --run development/qwen_interface_consultation/run-001 --output <new-verification.json>
```

The verifier refuses an existing output and checks the frozen execution-code
hashes. Reproduce against this implementation, not an arbitrarily changed
future checkout. Run `scripts/analyze_interface_output_tokens.py` with the
selected local model/tokenizer paths and another new output path to reproduce
the separate text counts; this performs no inference.

The separate four-request design package has been natively prepared with zero
completion calls. It is outside this response schedule and has supplied no
model preferences to this run.
