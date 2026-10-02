# Retrospective preparation failure custody

Preparation001 failed at QualificationLog construction before any runtime,
native, checker or completion request. Its original empty folder was retained.
FAILED.json records the unchanged private traceback and log fingerprint.

The field published_revision in that retrospective record identifies the
surrounding published plan revision4db773d7; it does not mean run_url.py was
committed at that revision. The failing implementation was uncommitted.
failed-run_url.py preserves its exact bytes, reconstructed by reversing only
the initializer/closure repair and verified against the pre-repair SHA-256
already recorded in FAILED.json. Neither the original private log nor failed
source bytes have been changed. Prospective preparation uses a new002 folder.
