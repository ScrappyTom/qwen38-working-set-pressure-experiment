# Uncoached contribution preparation

Prepared and qualified; no Qwen completion requests have been sent. Read the
[preparation review](PREPARATION_REVIEW.md), [task](TASK.txt), [specification](SPEC.md)
and [focused checks](TESTING.md). The [execution manifest](EXECUTION_MANIFEST.json)
binds preparation-001, the current implementation, unchanged model settings and
separate limits of 16 new model requests / 24 actual operations.

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

Future execution is a separate identified attempt. Close it before any Qwen
design consultation or host repair. Directly review the actual inputs, complete
responses, saved work and tool results afterward. No new effort policy, helper
inference, working account or required explanatory closing call is introduced.
