# Uncoached contribution

Completed under frozen c476ee9d: four Qwen requests and five actual operations
produce a checked submission without coaching. Read the [results](review/RESULTS.md),
[complete transcript audit](review/DIRECT_TRANSCRIPT_AUDIT.md),
[host path](review/HOST_PATH_AUDIT.md), [construction finding](review/APPARATUS_FINDING.md)
and [execution receipt](review/EXECUTION_RECEIPT.md). The
[saved patch](run-001/diffs/EVT-0042.patch) adds three meaningful transport tests and
preserves all earlier work. The task loop takes 52.863 minutes; successful use of
the host does not establish efficient or sustained autonomous work.

The original [preparation review](PREPARATION_REVIEW.md), [task](TASK.txt),
[specification](SPEC.md) and [focused checks](TESTING.md) remain unchanged.
The [execution manifest](EXECUTION_MANIFEST.json) binds preparation-001 and the
unchanged model settings. Its allowance is consumed and closed: 12 unused
requests and 19 unused operations are not available for a retry or successor.

The automatic runner supplies the declared task/state and actual host feedback.
It incorporates the corrected wire format and optional requested edit/check pair;
there is no reviewer dialogue during execution. The completed library, parsing
regression and documentation are the starting work. The new contribution adds
copying/serialization regression coverage that those saved tests do not exercise.

Preparation also exposed and corrected a [check-scope defect](check-scope-probe-001/README.md):
a prior task's passing check could authorize a different task on the same candidate.
The opt-in session now requires both candidate and checker definition to match.
Historical records and host implementations remain unchanged.

Both compact and broad-reading scripted paths complete and replay exactly. They
use native rendering/tokenization but substitute explicitly labeled scripted
responses; they are not autonomous model outcomes. The reference test is used
only in those offline candidates, never in the proposed model's initial candidate
or supplied task input. See [verification](VERIFICATION.json) and the sealed
[qualification](preparation-001/QUALIFICATION.json).

Any future comparison is a separate identified attempt. Keep design consultations
outside active runs. Directly review actual inputs, complete responses, saved
work and tool results. This tranche introduces no new effort policy, helper
inference, working account or required explanatory closing call. Its next
recommendation is a bounded reasoning-allocation comparison; the observed
output-encoding difficulty stays explicit rather than being dismissed as solved
merely because the final payload was valid.
