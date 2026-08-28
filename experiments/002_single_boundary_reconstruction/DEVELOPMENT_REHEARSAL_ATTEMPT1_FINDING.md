# Development rehearsal attempt 1 finding

The second development-only lifecycle sent one setup request to the dedicated
llama.cpp endpoint. The server returned HTTP 400 before sampling because its
JSON-schema-to-grammar converter could not parse a single-option `oneOf` setup
schema. The server log records zero decoded tokens. Qwen therefore produced no
assistant response, and no measured fixture was loaded or exposed.

The exact outbound coding request, endpoint request, rendered prompt, record
chain, runtime launch, and server log are preserved under
`development_live_rehearsal_attempt1_schema_failure/`. The historical adapter
did not retain the HTTP error response body; the server log retains the exact
failure classification.

The earned amendment makes the one legal setup action a direct strict object
schema, matching the previously live-qualified donor protocol. Multi-action
prefix and continuation schemas remain strict unions. It also makes all future
HTTP error bodies bounded and immutable in custody before raising a terminal
transport stop. These changes affect transport qualification only; they do not
change tasks, conditions, model-visible request content, the actor, sampler,
capacity limits, or measured-bank bytes.
