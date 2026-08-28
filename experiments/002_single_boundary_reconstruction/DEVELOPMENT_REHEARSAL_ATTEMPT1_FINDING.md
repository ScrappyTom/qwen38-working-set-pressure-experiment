# Development rehearsal attempt 1 finding

The second development-only lifecycle completed its setup call: Qwen returned
the exact valid action `{"action":"begin"}`. The following first prefix-work
request reached llama.cpp, but the server returned HTTP 400 before sampling
because its JSON-schema-to-grammar converter could not parse the larger work
union. The server log records zero decoded tokens for that second call. No
source-acquisition behavior occurred, and no measured fixture was loaded or
exposed.

The exact outbound coding request, endpoint request, rendered prompt, record
chain, runtime launch, and server log are preserved under
`development_live_rehearsal_attempt1_schema_failure/`. The historical adapter
did not retain the HTTP error response body; the server log retains the exact
failure classification.

The earned schema correction uses a direct strict object for setup and matches
the previously live-qualified donor geometry for work: integer domains receive
finite maxima, and patch strings are constrained to the admitted 512-byte
source-line geometry rather than the broader host fallback. Multi-action
prefix and continuation schemas remain strict unions. All future HTTP error
bodies are also bounded and immutable in custody before raising a terminal
transport stop. These changes affect transport qualification only; they do not
change tasks, model-visible coding-request content, conditions, actor, sampler,
capacity limits, or measured-bank bytes.
