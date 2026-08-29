# Experiment 011 completion-supplement apparatus finding

## Disposition

The separately authorized completion supplement completed cleanly. It ran only the previously missing `E11-OBS-KAPPA` / seed `223607` pair under a fresh shared prefix, in frozen order `T25-L0` then `T25-L1`. It is classified as `post_interruption_completion_supplement_not_rewrite_of_primary_attempt`.

The original primary run remains immutable, interrupted, and formally unscorable. This supplement does not resume its terminal call, replace its evidence, or retroactively convert it into a complete primary run.

## Exact execution

- Authorization SHA-256: `590410d85c3c294e65b37c51009a85ed79e5657f1a4efd954d83ffe984d3babd`.
- Prior partial seal SHA-256: `39d58e0b55c949609ad4c33ad0034219fdf7f35352fda29f4f043d4eb8f75d96`.
- Completion seal SHA-256: `89b3ef24cd78fe3f7c45e662f6dca7226581cb121114763735bdf3f276f5b3bf`.
- Completion aggregate SHA-256: `b8326cede53484f7f78df4749a19b53a23126e9b776f0f029023f14a5ad3cb7b`.
- 35 prepared invocations and 35 HTTP completions.
- One fresh shared prefix, one L0 branch, and one L1 branch.
- Zero retries, repairs, rescues, rejected actions, parser failures, capacity denials, or checker failures.
- All five complete record chains replayed.
- Runtime token-accounting delta was zero on all 35 calls.
- Evaluator truth remained unopened until the response seal existed.
- The owned llama.cpp process shut down and port 18114 was released.

Both branches reached the second boundary, passed the Phase-C public check, submitted candidate `3136bff2d3b67f7b8cdd3ebf414d14b4fd77a4a2d2b73058eb3b183ae192a244`, and passed hidden grading.

## Detached lifecycle

The run was launched by an independent Windows process rather than by a tool-session-owned interactive process. Its PID, stdout, and stderr were written under `C:\e11-launch`, while all sealed experimental evidence was written under `C:\e11-completion`. The runner survived repeated monitoring command completion and owned the server through verified shutdown. This closes the specific lifecycle failure that interrupted the original run.

There was one pre-exposure launcher failure before this run. The first detached launcher attempted to place redirect files directly under `C:\`, and Windows rejected `Start-Process` with access denied. No output root, server process, endpoint request, GPU activity, or model response was created. The launcher was corrected prospectively to use the dedicated `C:\e11-launch` directory, its new SHA-256 was bound into a replacement authorization record, and that source-only correction was committed before the one model-exposed attempt. This event is not a retry of an actor call because no actor or server lifecycle began.

## Host-path audit

No host defect affected either outcome.

- The model-visible requests were constructed under the authorized completion executable closure.
- The common prefix crossed the first boundary after the required reads, patch, `prefork` check, `vector` probe, and `fork_ready`.
- Both branches received the same task, candidate, exact active-phase pointer, P0 directory, observation identities, budgets, and latest fork result.
- The only treatment difference was the read contract: actor-selected `line_count` in L0 versus deterministic maximal bounded pages in L1.
- Every model action was accepted exactly as emitted.
- Candidate, file, observation, check, and submission bindings remained exact.
- Both model-visible checks in each branch passed, and the post-seal hidden grader independently passed both final snapshots.

The full response-side evidence is indexed in `COMPLETION_TRANSCRIPT_INDEX.json`. Mechanical replay and grading are in `COMPLETION_MECHANICAL_RESULTS.json` and `COMPLETION_POSTSEAL_HIDDEN_GRADING.json`.

## Validity boundary

The supplement provides valid measured evidence for one separately authorized pair. A combined four-pair table is useful descriptively, but it is mixed-source evidence: three pairs came from the original interrupted run and the fourth came from this later fresh-prefix supplement. It must not be reported as the untouched original four-pair primary result.

No automatic successor experiment is authorized by this finding.
