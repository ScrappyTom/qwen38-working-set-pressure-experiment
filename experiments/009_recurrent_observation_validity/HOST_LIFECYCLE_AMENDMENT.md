# Experiment 009 owned-server lifecycle amendment

## Trigger

After the successful Epsilon development rehearsal, the listening port was
released but a `llama-server.exe` process remained. Historical receipts equated
`port_free(port)` with complete server shutdown, and historical launch records
did not record the spawned child PID. That was not enough to prove resource
closure.

## Prospective contract

Before launch, the host now requires both:

- the dedicated port is bindable; and
- no process with the exact frozen runtime image name is present.

At launch, custody records the exact spawned PID alongside the executable and
arguments.

At shutdown, the host:

1. terminates the exact spawned child;
2. waits up to 30 seconds;
3. kills that exact child if necessary and waits again;
4. closes captured output streams;
5. waits for the dedicated port to become bindable;
6. records child return code, child-termination status, port status, and the
   combined verdict in `runtime/shutdown.json`;
7. fails closed unless the exact child has exited and the port is released.

Readiness failure and readiness timeout invoke the same cleanup path. A port-
only shutdown receipt is no longer accepted by the Experiment 009 development
or measured entrypoint.

## Scope

This amendment changes lifecycle custody and preflight only. It does not change
the actor, model-facing prompt, sampler, tool semantics, observation directory,
candidate state, schedule, bank, or evaluator. The executable closure and
measured package must nevertheless be regenerated because project source bytes
changed.

The prior Epsilon response evidence remains immutable. Its historical
`server_shutdown_verified` value is not rewritten; the direct audit explains
why that old port-only field is insufficient.
