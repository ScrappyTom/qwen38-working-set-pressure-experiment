# Experiment 004 attempt 1 apparatus finding

## Disposition

The response tree is sealed and replayable, the actor/runtime lifecycle completed
without an infrastructure failure, and evaluator truth remained unopened until
after the seal. The attempt nevertheless does **not** qualify the prospectively
named `R1 = low reasoning with a hard 512-token budget` treatment.

Two independent limitations determine that disposition:

1. `E4-SOURCE` exhausted all 18 shared-prefix calls before reaching a fork, so
   neither R0 nor R1 was exposed for that case.
2. The live server was launched with `--reasoning-budget -1`. Although every R1
   endpoint request contained `reasoning_budget: 512` and
   `reasoning_effort: low`, llama.cpp did not enforce the per-request budget.
   The third R1 private reasoning trace tokenizes to 809 tokens with the pinned
   tokenizer. The five traces tokenize to 262, 218, 809, 275, and 106 tokens.

The one completed R0/R1 matched pair is valid exploratory evidence for
reasoning-off versus reasoning-enabled/low-requested behavior. It is not a
hard-512 comparison.

## Evidence integrity

- actor: `Qwen3.8-27B-AD-IQ2_S.gguf`
- actor SHA-256:
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`
- runtime: llama.cpp `b10434-7e4c0a968`
- response aggregate SHA-256:
  `0612c9e6881585c42e7f7cf54600b25e05582499dd7150a31f242cf4c18fcbbf`
- completion calls: 39
- retries, repairs, rescues: 0
- evaluator reads before response seal: false
- server shutdown and dedicated-port release: verified
- hidden grading occurred only after the sealed tree was copied into the
  repository.

`scripts/analyze_reasoning_study.py` verifies the copied response tree against
the pre-evaluator seal, replays the eligible prefix and both completed branches,
and independently executes the hidden grader against each terminal candidate.

## Prefix-screen finding

The shared prefix was intended to create an authentic pressure boundary before
the R0/R1 fork. It proved unsuitable as the isolating mechanism for this narrow
diagnostic.

`E4-SOURCE` used one `begin` action and seventeen reads. The actor requested
seven 10-line pages and one large completing page for `archive/amber.py`, then
did the same for `archive/cobalt.py`, and spent its final call on the first ten
lines of `archive/ivory.py`. It never reached `policy/namespace.py`, the staging
repair, the prefork check, or the fork. This is a model-policy outcome under the
frozen prefix, but it means the source R0/R1 treatment was never instantiated.

`E4-OBSERVATION` reached the fork in eleven calls. It probed the routing service,
read the three archives in one request each, read the staging target, called the
prefork check prematurely, patched the staging target, called `fork_ready`
prematurely, then passed the check and called `fork_ready` successfully. The two
recoverable ordering mistakes are part of the common prefix and therefore do
not favor R0 or R1.

The source-prefix failure does not justify increasing the live prefix budget.
For a narrow post-reset reasoning diagnostic, a mechanically constructed exact
fork is the cleaner isolating mechanism. It must be described as a constructed
post-reset diagnostic, not as a second authentic-pressure result.

## Runtime-budget finding

The request-side field was not an enforceable bound in this configuration. The
server launch was authoritative and explicitly unrestricted:

```text
--reasoning auto
--reasoning-format deepseek
--reasoning-budget -1
```

The pinned binary's own help defines server `--reasoning-budget N` as the token
budget for thinking. A successor may use a server-side value of 512 while still
selecting reasoning off/on through the per-request chat-template setting. That
behavior must be demonstrated on development-only material before any new
measured bank is exposed.

No additional measured call is authorized by this finding.

