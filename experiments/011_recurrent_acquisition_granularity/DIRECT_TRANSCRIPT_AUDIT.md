# Experiment 011 direct transcript audit

## Review method

This is a condition-aware, post-seal corrective audit by the primary Codex project agent on 2026-08-29. I directly inspected all 108 saved coding requests, rendered prompts, endpoint responses, private reasoning outputs, strict JSON actions, and model-visible results. I also inspected the exact request-side artifacts for the interrupted 109th HTTP attempt, which has no response.

The audit did not infer behavior from aggregate diagnostics alone. Artifact hashes and per-call paths are in `TRANSCRIPT_INDEX.json`; replay and hidden-grade results are in `MECHANICAL_RESULTS.json` and `POSTSEAL_HIDDEN_GRADING.json`.

## What Qwen was given

All post-boundary branches used the same AD-IQ2_S actor with server-enforced low reasoning capped at 512 tokens. This was not a thinking-on versus thinking-off comparison.

At each reconstruction Qwen saw:

- the exact full authorized task;
- one byte-exact active-phase pointer authored prospectively by the task author;
- exact completed-phase IDs;
- the exact current candidate ID;
- a readable P0 directory of current paths, symbols, signatures, ranges, and sizes;
- observation-directory v2 entries containing handle, action, target, candidate binding, size, and hash, but no semantic body preview;
- exact invocation budgets;
- ordinary exact tools and `reopen_observation`;
- no earlier append-only chronology beyond the frozen reconstruction contract.

Condition identity was not named. The model-visible treatment was only the physical read contract:

- L0: `read(path, start_line, line_count)`, described as actor-selected exact whole-line paging.
- L1: `read(path, start_line)`, described as the largest exact current whole-line page fitting the frozen result bound.

There was no read suppression, cache hit, summary, ranking, relationship graph, or host-selected relevance in either branch.

## Shared prefixes

Cells 1–3 completed their shared prefixes coherently. Qwen read all three required 191-line archive files, read and repaired `stage/ready.py`, passed `prefork`, called the compatibility probe, and crossed the first authentic boundary. It sometimes read the two-line Phase-B label target before `fork_ready`; the host preserved that exact extra acquisition but did not carry it as hidden relevance into the reconstructed branch.

Cell 4 began identically. Qwen emitted `begin`, then complete reads of `archive/hazel.py` and `archive/ivory.py`. Its reasoning accurately tracked that `archive/jade.py` remained. The exact call-4 request asked for that file. The external host terminated while the server was processing this admitted request; Qwen produced no saved response.

## Pair 1 — IOTA, seed 173205

### Common semantic behavior

Both branches immediately selected `OBS-0002`, whose candidate binding matched the current Phase-A candidate, reopened the exact `H2@@` marker, read `harbor/label.py`, produced the same correct patch, passed `public`, and captured the new current-candidate marker `J7@@`.

The conditions diverged only at the two required 198-line bridge files.

### L0

Qwen chose 100-line physical pages despite P0 showing each governing function at lines 197–198. It read:

1. `bridge/dahlia.py` lines 1–100;
2. `bridge/dahlia.py` from 101, completing the file;
3. `bridge/ebony.py` lines 1–100;
4. `bridge/ebony.py` from 101, completing the file.

Its reasoning correctly tracked each continuation and did not misunderstand the task. After call 9 it had acquired every required byte, made the correct mutation, passed the check, and captured the new observation. The exact next request would have been the mechanical `fork_ready`, but the extra page actions and their repeated JSON/reasoning/history framing raised that request to 22,299 offline prompt tokens. With the frozen output, reasoning, and runtime allowances, the 25k guard denied it before HTTP.

This is not a semantic failure. It is the intended physical-acquisition failure class: correct evidence policy, inefficient page size, lost closure.

### L1

Qwen chose each file and start line; the host returned all 198 lines in one bounded exact page per file. Qwen then called `fork_ready` on call 8, crossed the second boundary, compared the older and current candidate bindings, selected and reopened current `OBS-0005`, read `harbor/header.py`, applied `J7@@`, passed `public`, and submitted. The terminal candidate passed hidden grading.

This pair is direct evidence for the mechanism under test. L1 removed two low-value physical decisions and converted an otherwise correct but capacity-stopped path into a completed recurrent trajectory.

## Pair 2 — IOTA, seed 223607

L0 did not fragment the bridge files. Its private reasoning used P0's 197–198 end range and deliberately selected `line_count: 250`, so each file completed in one call. L1 mechanically did the same physical transfer. Both Phase-B paths used eight calls, reached the second boundary, chose current `OBS-0005` rather than stale `OBS-0002`, patched the header correctly, passed, and submitted hidden-correct candidates.

L1 made one extra Phase-C read of `harbor/wire.py`. Its reasoning said it wanted to confirm the explicit ASCII-preservation clause before patching. L0 relied on the visible task and current header source without opening the wire file. This added one call and 4,511 prompt tokens to L1 without changing quality. It is ordinary model-policy variation, not a mechanical requirement of maximal paging.

## Pair 3 — KAPPA, seed 173205

Again, L0 selected a sufficiently large page (`line_count: 200`) for each 198-line bridge file. L0 and L1 therefore both used eight Phase-B calls and reached the second boundary. Both reopened the old Phase-A marker `Q5^^`, repaired `vector/label.py`, passed, captured the new `X8^^` marker, and acquired both bridge files completely.

At Phase C both conditions selected current `OBS-0005` and rejected the older candidate-bound observation in their reasoning. L0 reopened the observation before reading the header. L1 read the header first, then reopened the observation, then opened `vector/wire.py` to confirm the ASCII constraint. Both exact patches were correct, both public checks passed, both submitted, and both hidden graders passed. The L1 confirmation read added one call and 4,358 prompt tokens without quality gain.

## Observation validity behavior

Across all five completed Phase-C trajectories, Qwen chose current `OBS-0005`, not stale `OBS-0002`. Its reasoning explicitly compared candidate IDs and identified the newer probe as the applicable fact. It then used the exact reopened marker in the patch.

After mutation, Qwen sometimes questioned whether an observation marked `current_candidate_only` remained valid now that the patch had produced a successor candidate. That concern is logically understandable: the instruction means to use evidence bound to the pre-mutation current candidate, while the phrase can sound invalid immediately after mutation. Qwen nevertheless followed the prospective sequence—reopen before mutation, patch, check—and all five terminal candidates were correct. This wording tension did not affect an outcome, but it should remain visible if later tasks use more complex validity semantics.

## Reasoning behavior

The low bounded reasoning was dominated by explicit task restatement and checklist bookkeeping. Qwen repeatedly reconstructed which phase steps were complete and usually chose the next action correctly. This helped preserve purpose and candidate/observation binding through resets.

It did not reliably optimize physical headroom. In pair 1, the request displayed both the remaining invocation budget and P0's file-end ranges, yet Qwen chose 100-line pages. In pairs 2 and 3 it chose 250 and 200 lines respectively and completed each file in one call. The same actor therefore possessed the information needed for an economical choice but used inconsistent heuristics across seeds.

The behavior is not unclear enough to justify a thinking-mode rerun. Private reasoning is already available and directly explains the actions. The failure is not inability to infer file extent; it is unstable local physical-transfer policy near a hard global budget.

## Host/model separation

- The designed L0 capacity denial was a host guard and produced no model response.
- The cell-4 interruption was an external host-lifecycle failure and produced no model response.
- Every other saved action was emitted by Qwen and accepted exactly as emitted.
- No rejected action, parser repair, retry, rescue, or hidden host continuation occurred.

## Qualitative conclusion

The partial transcripts support a narrow claim:

> Deterministic maximal exact paging helps when Qwen's chosen physical page size fragments a known complete-read obligation near a context boundary. It is neutral when Qwen already chooses a page large enough, and it does not eliminate unrelated confirmation reads.

The model understood purpose, current versus stale evidence, mutation, checking, and closure. The observed reliability loss was the mechanical cost of a low-value page-size choice, not missing semantic information.
