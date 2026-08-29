# Development timeout amendment

The first focused final-path rehearsal prepared one exact request and launched
one HTTP call. The actor/server remained actively decoding after 600 seconds;
the host's fixed HTTP timeout fired before any assistant response was returned.
No measured case was exposed and no model action occurred.

This was an apparatus failure. At timeout, llama.cpp had processed all 2,583
prompt tokens and generated 251 tokens without truncation. The host preserved
the exact request, rendered prompt, endpoint request, transport-stop record,
server log, candidate, and launch identity. The owned server was then stopped
and port 18110 released. Evidence is sealed under `attempt1_timeout/`.

The timeout is revised from 600 to 14,400 seconds. The bound is derived from
the qualified physical worst case on this host:

```text
50,176 prompt tokens / 7 prompt tokens per second
+ 2,500 output tokens / 1.1 generated tokens per second
= about 9,441 seconds
```

Four hours is therefore a transport-hang sentinel above the physical admitted
workload, not a model time budget. It does not alter model-visible bytes,
sampler, reasoning cap, context/output limits, action budget, or response
handling.

The global monitor is also corrected: `external_call_stopped` and
`capacity_stopped` now resolve a prepared invocation even though they do not
produce an accepted `action_result`. The old monitor incorrectly reported the
timed-out call as still in flight after the terminal transport-stop record.

Both changes require fresh source closure and offline qualification. A new
fresh development sibling must be used for the next live final-path rehearsal;
the timed-out call will not be retried or completed retrospectively.
