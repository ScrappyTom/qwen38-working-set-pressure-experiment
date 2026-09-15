# Execution and closure receipt

The owner said Proceed after readiness for the frozen run. The execution command
recorded that direction and started one new eight-request/twelve-operation attempt
at commit `feb7b62b3684aed1c6f7015ed1c9efdfa73e4ea9`. Host implementation is
02e153744b72c99f164b3ce5ee03e288a4118eb7. No consumed allowance was reused.

The reservation is recorded at 2026-09-15 02:43:26 UTC (September 14 local time).
The task loop closes at 03:12:15 UTC and runtime closure at 03:12:17 UTC. All eight
sent responses return, are preserved and execute one operation each. Disposition
is request_allowance_exhausted, with no operator stop, retry, coaching or ninth
request. Four unused operations are closed.

| Binding | Value |
|---|---|
| Seed | 961213 |
| Actor | Qwen3.8-27B UD-IQ3_XXS |
| Model SHA-256 | c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee |
| Runtime revision | 7e4c0a96880dae4fc4268ad441f8a6446bd5460a |
| Thinking | On, medium, uncapped; no prompt cache reuse |
| Sampler | Temperature 1.0, top_p 0.95, top_k 20, min_p 0, repeat penalty 1.0, frequency/presence penalties 0 |
| Context/cache/MTP | 56,576; q4_0 K and V; MTP disabled |
| Input ceiling / prospective generation reserve | 23,808 / 32,768 tokens |
| Starting candidate | da233419db36b8dd9e943765a37b2d4fdfab6c17b7e9018ab239a0710eec9577 |
| Final candidate | 4fcb261b9c8d30ed0a10690a3db251d3b51f74e2a3698d2e29fbf4a294d8ad73 |

The [response seal](../run-001/RESPONSE_SEAL.json) file SHA-256 is
`822b0c25eeeb4196f60fbc4c18f4e6d017b2fcc073300c217bd1ccef3fc573ef`.
Its inventory aggregate is
`969b5d4df739a611756127ec0e89ff949c022fb70f8a96e9c6ab36fde059143a`;
these are different hashes with different scopes. Exact verification reports eight
replies/operations, nine native inputs, 152 chained custody records and 280 source
identities. The final native input was admitted but never sent to a model.

All seven nonterminal results reach the next request completely. Both saved edits
are unchanged in review. Independent checker/documentation results were produced
only after sealing and never supplied as actor feedback. The full original run
and unsuccessful artifacts remain the evidence; review adds no experimental score.

The owned runtime closed normally, the dedicated port is free, and no CUDA failure
or truncation is observed. Minimum sampled GPU free memory is 151 MiB across 8,247
samples under the accepted advisory policy. Private runtime paths/logs remain local
and excluded from Git; their identity and lifecycle checks remain in the seal.
