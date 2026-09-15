# Execution record

Implementation and frozen preparation were committed and pushed at
`70e6e21ce7d2a24c593477b51dfda300610b4780`. Remote main was verified at that
revision before dispatch. The working tree was clean. Plan publication preceded
implementation at `5fe48c51`.

One `run-001` attempt began September 15, 2026, under manifest
`0cf9bb344314a61e976300c90bc4bf2bca1caa717a60497fa6a1b179e77823a1`.
Its first request has 4,661 tokens and exact wire SHA
`78f20369651cdcc92038a100c5fb5ee1ade42bb78ebee7aa523f1f8639829ab8`,
matching preparation. Seed 961221, sixteen requests/forty-eight operations maximum.
No reviewer input, reference contribution or replacement group enters the run.

The runtime helper's launch default remains xhigh, as in the preceding medium
configuration. Every actual request explicitly supplies medium; exact native
rendering is verified against the medium template envelope. The launch default
alone is not the effective reasoning setting. q4 KV, MTP disabled, context 56,576
and uncapped generation remain unchanged. Memory monitoring is advisory under the
previously accepted policy, with runtime/telemetry failures remaining stop conditions.

## Closure

C13 returns `finish_reason=length` with 19,871 input and 36,705 generated tokens,
an empty final field and no operation to execute. The attempt is closed without
retry at 2026-09-15 20:49:07 UTC. Thirteen requests returned; twelve were complete
executable replies and sixteen actual operations were recorded. Three requests and
thirty-two operations are unused and closed. No reviewer stop, coaching, rescued
draft or configuration change occurred.

The owned runtime shut down, its dedicated port is free, and the response seal
records aggregate SHA-256
`29952a36bf1f599649382e5526b25cfdbc9ccf30155e298e520fc55feed08399`.
Minimum sampled free GPU memory was 379 MiB; no CUDA failure was observed.
The incomplete response is a physical-context stop, not a memory-margin stop.

Exact replay verifies all 297 custody records, twenty-two native inputs, 294 bound
source identities and the twelve processed replies. The actual check observation
replays without re-execution. All thirteen full responses were subsequently reviewed
against their actual inputs. See RESULTS.md for outcome and remaining limitations.

## Publication correction

The new development directory was missing the repository's private-runtime ignore
rule. Consequently, twelve qualification `launch.json`/server log files entered
implementation commit 70e6e21c, despite the evidence seals designating them local-only.
This was a publication error, not a changed experimental input or runtime.

The closing revision adds the missing ignore rule and removes those files from the
current Git tree while retaining their exact local copies. The live attempt's three
private-runtime files are excluded before its publication. Earlier commit 70e6e21c
still contains the twelve qualification files; no history rewrite or claim that they
were never published is made. Local verification and their recorded hashes remain
available. Public experiment evidence is unchanged.
