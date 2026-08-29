# Experiment 012 apparatus finding

## Disposition

The authorized Experiment 012 primary run is complete, sealed, mechanically
valid, and formally scorable. It is a negative result for the frozen large-world
controller: no branch completed the four-phase task and no terminal candidate
passed the final hidden grader.

This was not a transport, parser, checker, evaluator, GPU, or lifecycle failure.
The run exposed a consequential controller limitation: after an in-phase 25k
reset, T25 retained the complete body of the latest action/result pair but did
not retain compact exact receipts for the other work already completed inside
the active phase. Qwen consequently repeated already-completed acquisition
until it exhausted the phase-call budget or the reset allowance.

That limitation affects the outcome, but it is part of the prospectively frozen
treatment rather than an unexpected apparatus deviation. Historical evidence
is therefore valid and must not be rewritten or rerun on the exposed bank.

## Exact execution state

- Actor: `Qwen3.8-27B-AD-IQ2_S.gguf`.
- Actor SHA-256:
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`.
- Runtime: llama.cpp b10434.
- Reasoning: server-enforced 512-token private budget, separately custodied and
  omitted from later chronology.
- Conditions: 50,176-token append-only C50 and 25,000-token reconstructed T25.
- Cases: two fresh 160-file, approximately 2.2 MiB worlds.
- Seeds: 173205 and 223607.
- Prepared invocations: 145.
- Completed HTTP calls: 129.
- Pre-HTTP capacity denials: 16.
- Retries, repairs, rescues: zero.
- Evaluator reads before response seal: false.
- Server shutdown and port release: verified.

The response seal covers every completed model response. Every completed call
has exact coding request, endpoint request, rendered prompt, endpoint response,
private reasoning, assistant action, and result custody. All 129 response IDs
are unique.

## Host-path validity

All 129 completed model actions parsed and were accepted. Runtime prompt-token
accounting delta was zero on every completion. Candidate, file, observation,
check, probe, and fork bindings remained exact. All 16 complete stage record
chains replayed.

Eight model-visible checks were executed: four shared-prefix `prefork` checks
and four C50 Phase-B `public` checks. All passed. T25 did not reach a check after
its first in-phase reconstruction, so no T25 check result was withheld or
misclassified.

The 16 calls prepared without HTTP divide mechanically into:

- four terminal C50 physical-context denials;
- ten T25 denials that triggered the prospectively frozen reconstruction;
- two final T25 denials after the four-reset allowance was consumed.

The two source-case T25 branches ended differently: each consumed all fourteen
permitted HTTP actions after two in-phase reconstruction denials, so the host
did not offer a fifteenth call. The two observation-case T25 branches ended on
their fourth in-phase prospective capacity denial, before HTTP, after eleven
and twelve completed actions respectively.

These distinctions are preserved in the host-path audit. A denied prospective
request is not counted as a Qwen response, and a call never offered after phase
budget exhaustion is not described as a model refusal.

## Post-seal candidate characterization

The final hidden grader correctly failed all eight incomplete branches. That
terminal result hides useful milestone information, so the exact saved
candidates were also run against the already-frozen phase checkers after the
response seal:

- every C50 and T25 final candidate passed the Phase-A checker;
- every C50 and T25 final candidate passed the Phase-B checker;
- both observation-case C50 candidates also passed the Phase-C checker;
- no branch passed the Phase-D checker or final hidden grader.

Thus T25's failure was not failure to understand or implement the first
post-boundary mutation. All four T25 actors produced the correct Phase-B
candidate before losing closure. C50 formally closed Phase B in all four paths,
and its two observation paths also produced the correct Phase-C mutation before
physical capacity prevented the remaining required reads/check/fork.

Post-seal phase checking is diagnostic only. It does not retroactively add a
model-visible check, fork, completed phase, or submission.

## Outcome-affecting controller limitation

The request contract labels reconstructed history as
`fresh_context_exact_task_current_world_latest_boundary_result_only`. During a
reset inside a phase, the implementation actually keeps the last complete
action/result pair, whatever its type. In this study that pair was usually a
14.4 KiB exact ledger read. Two properties followed:

1. the fresh context still began with a large evidence body rather than a small
   receipt and exact reopen handle;
2. earlier accepted actions in the same phase disappeared from model-visible
   history even though their effects and host-side gate state persisted.

Candidate mutation survives because it changes the exact current candidate.
Read completion does not change the candidate, so Qwen cannot recover it from
world state. The host's required-read gate remembered the reads, but the model
did not know that the host remembered them. Qwen therefore reopened the same
observation and reread the same exact files instead of proceeding to
check/probe/fork.

This is not silent host-selected relevance or a checker defect. It is a missing
mechanical continuity object. The scalable form is not a semantic summary; it
is a compact exact in-phase action/effect ledger whose evidence bodies remain
externally custodied and reopenable.

## Environmental and custody validity

The owned llama.cpp server launched on the frozen port, served only the
authorized schedule, and shut down normally. No competing project server or
GPU lease altered the run. The exact external evidence root remains at
`C:\e12-primary`; a byte-for-byte file-count and byte-count copy is preserved
under `measured_run/` in the experiment directory.

The large-world bank, execution package, authorization, actor, runtime profile,
schedule, and executable closure were verified before launch. No measured file
was regenerated after actor exposure.

## Validity boundary

Experiment 012 supports a clean conclusion about this frozen controller on
these larger synthetic worlds. It does not support a claim that exact bounded
reconstruction is generally incapable, because the study identifies a narrower
failure in in-phase progress representation. It also does not establish
repository-scale P0 search quality: many required paths were verbatim in the
user-authored phase text, while P0's most consequential use was locating the
small `policies` directory.

No automatic successor experiment, same-bank rerun, semantic summary,
relationship graph, ranking mechanism, read suppression, or evidence cache is
authorized by this finding.
