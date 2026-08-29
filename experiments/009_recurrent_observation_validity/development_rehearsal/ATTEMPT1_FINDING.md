# Development rehearsal attempt 1 finding

## Disposition

This development-only run was intentionally stopped during prepared call 3
after two completed HTTP/model calls. It exposed no measured case. Its exact
responses are sealed under `attempt1_cache_economics/` and are not resumed,
repaired, or reclassified as a completed rehearsal.

## Direct input/output review

Call 1 showed Qwen the complete fresh three-phase `relay` task, initial P0,
setup-stage capability surface, and only the legal `begin` action. Its private
reasoning accurately decomposed all three phases, explicitly identified that
Phase C requires the current rather than stale candidate-bound observation,
noticed that only `begin` was currently legal, and emitted:

```json
{"action":"begin"}
```

The host accepted it and offered call 2.

Call 2 showed the same task plus the accepted begin result and the prefix tool
surface. Qwen stated that it needed to read the three archive files exactly and
selected:

```json
{"action":"read","line_count":191,"path":"archive/acacia.py","start_line":1}
```

The host returned the complete 191-line, candidate-bound file. Call 3 was fully
prepared and custodied but interrupted before an endpoint response.

## Cache/economics finding

The first call took 541 seconds: 1,222 prompt tokens at 7.49 tokens/s and 519
completion tokens at 1.37 tokens/s. The second took 296 seconds: 1,167 prompt
tokens at 7.16 tokens/s and 182 completion tokens at 1.36 tokens/s.

Call 3 contained 9,622 prompt tokens because it included the newly returned
exact custody file. llama.cpp restored a 166-token checkpoint and began
processing the genuinely new history. An initial hypothesis that canonical JSON
key order had defeated cache reuse was rejected after inspecting the exact
checkpoint log: call 3's large result had never appeared in a prior prompt and
therefore could not already be cached. No prompt-layout change was earned or
made.

The important economics conclusion is narrower: replaying inert pressure
ledgers through a full live development trajectory would spend hours proving
prefix/middle transport already exercised in Experiments 007/008. It is not the
remaining host-v2 uncertainty.

## Next rehearsal boundary

The fresh `E9-DEV-OBS-DELTA` rehearsal mechanically constructs the already
qualified second-boundary state, including:

- exact Phase-B successor candidate;
- one exact stale observation bound to the prior candidate;
- one exact current observation bound to the current candidate;
- exact reopenable bodies and hashes;
- exact recurrent binding;
- `second_boundary_eligible` host-v2 disposition.

Real Qwen then receives the exact reconstructed Phase-C request and must choose
an observation, read/patch the target, check, and submit. This directly tests the
new operational final path in a small number of live calls. The offline bank,
closure, authorization, and candidate-binding test pass. It remains
development-only and cannot support the measured hypothesis.
