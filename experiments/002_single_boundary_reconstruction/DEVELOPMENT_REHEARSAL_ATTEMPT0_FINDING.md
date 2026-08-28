# Development rehearsal attempt 0 finding

The first development-only live lifecycle stopped before any completion call.
The owned llama.cpp server reached readiness, but writing the initial candidate
snapshot crossed the Windows legacy path-length boundary. The actor received
no coding request, the fresh measured bank was neither loaded nor exposed, and
the server shut down with its dedicated port released.

The preserved evidence is under
`development_live_rehearsal_attempt0_path_failure/`. Its receipt records the
exact `FileNotFoundError`, actor and bank identities, zero measured exposure,
and successful shutdown. The server log contains no chat-completion request.

The earned correction shortens only internal custody snapshot directory names
from a 64-hex candidate identity to a 32-hex (128-bit) prefix. Complete
candidate identity remains in every record payload and snapshot file bytes
remain hash-bound. A prospective Windows path-budget check now runs before
server launch. This changes no task, prompt, tool result, condition, model,
sampler, capacity rule, or measured-bank byte.
