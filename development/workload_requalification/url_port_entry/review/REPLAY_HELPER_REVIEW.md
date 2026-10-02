# Prospective closed-run replay helper

`verify_run.py` is evaluator-only and outside the task's bound implementation
glob. It was syntax-parsed and independently reviewed before a URL model attempt;
it has not been executed. Root authorizes its use only after `RESPONSE_SEAL.json`.
It defaults to version002, preserving the separate failed preparation001.

The helper connects the published/executed manifest to the exact preparation and
source closure, validates inventories and custody chains, and uses saved native
request/template/tokenization bytes for admission without making native requests.
It checks the actual sent wire inputs, validated public finals and usage, every
operation and receipt, candidate/version/account/selection checkpoints, preceding
feedback, typed diff restoration, raw observations, and final accounting/closure.
The replay store cannot execute checkers; a subprocess guard also rejects that
path. A partial or malformed response remains inert. Failure reports preserve
the helper digest and traceback without overwriting an earlier different failure.

Peer review found no concrete blocker after reconciling one false lead. A claim
that preparation002 lacked the private-runtime side map had been inferred from a
truncated full-seal display. Direct JSON key enumeration showed the actual map,
with three local runtime bindings; its regular inventory excludes those paths.
The concern was withdrawn and the strict check retained. This was a review
correction, not an execution failure or a production patch.

Mechanical replay is not semantic review. Root and independent reviewers still
need to read what Qwen actually received and produced, assess its use of feedback,
and inspect the final assertions, prose, examples and preservation directly.
