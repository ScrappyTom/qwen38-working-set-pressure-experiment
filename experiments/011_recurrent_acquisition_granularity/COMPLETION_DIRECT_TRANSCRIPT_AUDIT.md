# Experiment 011 completion-supplement direct transcript audit

## Review method

This is a condition-aware, post-seal audit by the primary Codex project agent on 2026-08-29. I directly inspected all 35 saved coding requests, rendered prompt/request bindings, endpoint responses, private reasoning outputs, strict JSON actions, and model-visible results. Large required custody files were checked as the exact complete read results Qwen received, including their candidate and file bindings, returned line ranges, completion flags, and source contents.

The review was performed after the response set sealed. It did not infer model behavior solely from receipts or aggregate metrics.

## What Qwen saw

The shared prefix presented the full three-phase task and exact append-only chronology under the 50k actor slot. After the first authentic boundary, each treatment received a fresh reconstructed context containing:

- the exact full user-authored task;
- the exact current user-authored phase text, without host semantic inference;
- exact completed-phase IDs;
- the current candidate ID;
- a task-independent P0 directory containing paths, symbols, signatures, line ranges, and file sizes;
- an exact observation directory containing handle, action, target, candidate binding, size, and hash, but no result-body preview or relevance ranking;
- the latest exact `fork_ready` action/result only;
- explicit invocation budgets and exact tool contracts;
- no older append-only chronology.

At Phase B the directory exposed three Phase-A records. `OBS-0002` was the `vector` probe bound to candidate `03fbb131...`. At Phase C it exposed both that older record and `OBS-0005`, the later `vector` probe bound to the current Phase-B candidate `13ea3261...`. The host did not mark either entry `stale`, reveal either marker, or choose a handle.

The only L0/L1 difference was physical paging:

- L0 exposed `read(path, start_line, line_count)` and described actor-selected exact whole-line paging.
- L1 exposed `read(path, start_line)` and described the largest exact whole-line page that mechanically fit the frozen bound.

There was no suppression, caching, semantic selection, summary, relationship graph, or automatic evidence reuse.

## Shared prefix: what Qwen did

Qwen began by restating all three authorized phases and then followed Phase A exactly:

1. read all 191 lines of `archive/hazel.py`;
2. read all 191 lines of `archive/ivory.py`;
3. read all 191 lines of `archive/jade.py`;
4. used P0 to locate and read the five-line `stage/ready.py`;
5. replaced `return 0` with `return len(PHASE_A_GROUPS)` using exact candidate/file bindings;
6. passed `prefork`;
7. called `probe("vector")` and received `vector_marker=Q5^^` bound to the patched candidate;
8. called `fork_ready`.

Its private reasoning was checklist-heavy but accurate. It repeatedly identified the remaining required step and did not touch Phase-B or Phase-C targets early. All required custody reads were complete, not previews.

## Phase B: identical semantic policy

Both branches immediately selected `OBS-0002` from the identity-only directory. Their reasoning connected its `probe` action, `vector` target, and candidate binding to the active Phase-B instruction. Reopening returned the exact body containing `vector_marker=Q5^^`.

Both then:

1. read the exact two-line `vector/label.py`;
2. patched it to return `"Q5^^" + name.strip().upper()`;
3. passed `public` on candidate `13ea3261...`;
4. called the new `vector` probe and received `vector_marker=X8^^` bound to that current candidate;
5. read all 198 lines of `bridge/kelp.py`;
6. read all 198 lines of `bridge/linen.py`;
7. called `fork_ready`.

The model preserved trimming and uppercase behavior. It did not infer the marker from metadata; it reopened the exact dynamic observation first.

### L0 paging

L0 examined P0's end range at lines 197–198 and chose `line_count: 200` for each bridge file. Each read completed in one action. This was already the economically adequate decision; there was no fragmentation for L1 to remove.

### L1 paging

L1 selected the same paths and start lines without a physical count. The host returned the same complete 198-line extents as deterministic maximal bounded pages. L1 did not obtain different semantic information.

Both Phase-B paths used eight calls and three reads. L1 consumed 55,962 prompt tokens versus L0's 55,948, a 14-token difference.

## Phase C: current-versus-stale selection

At the second reconstruction, both conditions saw six observation identities. The relevant alternatives were:

- `OBS-0002`: `vector` probe bound to older candidate `03fbb131...`;
- `OBS-0005`: `vector` probe bound to current candidate `13ea3261...`.

Both branches explicitly compared candidate bindings in private reasoning, selected `OBS-0005`, reopened its exact body, and extracted `X8^^`. Neither opened the stale observation.

Both then:

1. read the exact two-line `vector/header.py`;
2. patched it to return `"X8^^" + name.strip().casefold()`;
3. passed `public` on successor `3136bff2...`;
4. submitted that candidate.

The public and hidden graders both passed. Neither branch reread `vector/wire.py`; each preserved the existing behavior by changing only `vector/header.py`'s return expression.

Qwen briefly questioned in later reasoning whether a `current_candidate_only` observation becomes stale immediately after its consequential mutation. That is a reasonable wording tension, also observed in the prior run. It did not cause reacquisition, rollback, or a wrong action. The model followed the required sequence—select and reopen evidence while bound to the pre-mutation current candidate, mutate, check, submit.

## Paired economics

| Measure | L0 | L1 | L1 − L0 |
|---|---:|---:|---:|
| Phase-B + Phase-C calls | 13 | 13 | 0 |
| Read calls | 4 | 4 | 0 |
| Prompt tokens | 74,995 | 75,052 | +57 |
| Completion tokens | 5,593 | 5,951 | +358 |
| Endpoint time | 466,197 ms | 519,311 ms | +53,114 ms |
| Hidden pass / submit | yes | yes | tie |

The extra L1 time and completion tokens came from longer private reasoning, not an extra tool action or richer model-visible result. With one pair and fixed condition order, this is descriptive variation, not evidence that the paging contract itself causes slower reasoning.

## Qualitative interpretation

This missing pair confirms the neutral case of the treatment:

> When Qwen already chooses a line count large enough to satisfy the complete exact-read obligation in one action, deterministic maximal paging yields the same information, action count, candidate, check result, and hidden quality.

The transcripts also strengthen the controller result independently of paging. Through two reconstructed contexts, both branches preserved the active purpose, used candidate bindings to discriminate current from stale evidence, reopened exact dynamic facts, made consequence-bearing mutations, checked, and closed.

There is no unclear behavior here that warrants a thinking-mode rerun. The actor already ran with server-enforced low reasoning capped at 512 tokens, and its saved reasoning directly explains every selection. The treatment result is neutral because L0 made the adequate physical choice, not because the model's intent is unknown.
