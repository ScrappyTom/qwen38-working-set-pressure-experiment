# Host execution and custody

The separate dialogue adapter reuses the existing runtime, native rendering,
response preservation and sealing helpers. It supplies no response grammar,
function definition or tool channel, so the prose answer cannot execute a coding
operation. The actual host result records `executed: false`,
`candidate_mutated: false` and `tool_execution_enabled: false`.

Preparation and live input match byte-for-byte. The pinned offline tokenizer
independently reproduces the live count, and server usage reports no cached input.
All 87 source identities, original saved-work seal, public artifact hashes,
eleven chained records and locally private runtime files verify. The selected
actor, sampler, native thinking template, GPU offload, context allocation and
shutdown match their recorded contracts. The final answer and thinking are exact
extractions of the original raw response fields.

The dialogue log correctly records the selected 32,768 reserve. It separately
retains the helper's inherited 20,480 comparison; both are true for this response.
No historical reserve field was silently reinterpreted. The accepted GPU policy
is advisory and the actual 239 MiB minimum is preserved.

The independent verifier passed on its first execution, with zero model calls.
Its script is `scripts/verify_saved_work_dialogue.py`; output and execution log
are saved one directory above this review. That verifier intentionally checks
the frozen source closure. Reproduce it using the consultation source revision
and saved evidence after later host development; changing current host code does
not retroactively invalidate this verified run. No source patch was made in the
main checkout while the consultation could still consume D2.
