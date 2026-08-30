# Experiment 013

This experiment isolates the exact progress-state gap discovered in Experiment
012. See `SPEC.md`.

Current status: measured run complete, sealed, directly audited, and scorable.

Both conditions produced hidden-correct candidates in all four cells. Compact
receipts reached a passing public check in 4/4 branches versus 0/4 for the
latest-result baseline and submitted 2/4 versus 0/4, while using 53.1% fewer
Phase-B prompt tokens. The remaining observation-case failure was a repeated
check loop caused by presenting one phase through a frozen numbered receipt
prefix plus separate unsequenced post-reset history.

See `RESULTS.md`, `DIRECT_TRANSCRIPT_AUDIT.md`, and `APPARATUS_FINDING.md`.
