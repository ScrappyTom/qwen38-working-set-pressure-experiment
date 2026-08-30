# Experiment 014

This narrow fresh-bank study tests the residual Experiment 013 progress-surface
ambiguity: frozen receipt prefix plus recent history versus one monotonic exact
active-phase receipt sequence. See `SPEC.md`.

Current status: measured run complete, sealed, directly audited, and formally
scorable.

All eight final candidates passed hidden grading. The unified condition
submitted 4/4 versus 3/4 for the split condition. In the divergent fresh pair,
split history showed eleven passing checks but the fixed receipt prefix caused
Qwen to repeat until budget exhaustion; the unified sequence recorded the first
passing check as receipt 6 and Qwen submitted on the next turn. All stale-check
branches reran a current-candidate check after mutation before submission.

See `RESULTS.md`, `DIRECT_TRANSCRIPT_AUDIT.md`, and `APPARATUS_FINDING.md`.
