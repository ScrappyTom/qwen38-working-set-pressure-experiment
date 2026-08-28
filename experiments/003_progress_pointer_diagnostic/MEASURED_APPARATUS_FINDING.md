# Experiment 003 measured-apparatus finding

## Disposition

The measured run is apparatus-valid and behaviorally negative for the full pass criterion.

- response aggregate: `eceb7ee39aaa84d88f6a384824743f85d273151319a42e86e1591eba2b4e698a`
- completion calls: 36
- prospective requests: 39
- attempts per call: 1
- retries, repairs, rescues: 0
- infrastructure or integrity failures: 0
- response seal preceded evaluator access: yes
- server shutdown and port release: verified
- exact actor: `Qwen3.8-27B-AD-IQ2_S.gguf`
- actor SHA-256: `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`
- reasoning: off

The copied response tree reproduces all 295 files in the pre-evaluator response seal. Both shared prefixes replay mechanically. Every branch action/result pair re-executes against its exact forked candidate and matches stored results.

## Exposure and custody

The two cases were fresh before this run. The exact bank, schedule, first requests, progress pointers, actor, runtime, executable closure, and output root were frozen in commit `686cf46` before llama.cpp launch.

The observation probe was accepted once during its shared prefix. The next model request omitted both the probe capability and its response-schema variant. The exact result remained reopenable through `OBS-0001` after reconstruction.

No evaluator file was included in the execution package or read before the response seal. Hidden grading was performed only after copying and verifying the seal.

## Mechanical outcomes

| Fixture | Condition | HTTP calls | Terminal state | Mutation | Public check | Submit | Hidden pass |
|---|---:|---:|---|---:|---:|---:|---:|
| E3-SOURCE | T25-M | 3 | capacity stop before call 4 | no | no | no | no |
| E3-SOURCE | T25-P | 3 | capacity stop before call 4 | no | no | no | no |
| E3-OBSERVATION | T25-M | 4 | capacity stop before call 5 | no | no | no | no |
| E3-OBSERVATION | T25-P | 8 | continuation budget exhausted | no | no | no | no |

All four final candidates retain the valid Phase A readiness repair and the original flawed Phase B target. Hidden grading therefore fails all four without ambiguity.

## Valid interpretation

The run supports behavioral comparison of the exact pre-mutation trajectories. It does not support promotion of either 25k reconstruction condition.

The pointer was not inert. In both geometries it changed the first actions toward Phase B. It nevertheless did not produce mutation, closure, or hidden correctness. Detailed interpretation belongs to `DIRECT_TRANSCRIPT_AUDIT.md` and `RESULTS.md`.
