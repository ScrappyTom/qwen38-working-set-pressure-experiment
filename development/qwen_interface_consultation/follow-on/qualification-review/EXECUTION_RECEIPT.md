# Execution receipt — September 10, 2026

Owner authorization covered three qualification calls and four design calls
conditionally on qualification and direct review. The exact
[specification](../package/SPEC.md) was copied into the package before exposure.
Preparation made zero completions. Qualification sent/received/completed one
request, Q1; the remaining six were withheld after the GPU reserve breach.
There was no replacement attempt or design execution.

| Identity | SHA-256 |
|---|---|
| GGUF | c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee |
| b10434 llama-server | 5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610 |
| Offline tokenizer | d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c |
| Follow-on runner | f5c86b05d2b11ce90c1f4b030660e49e512f9294c2b77ad3048a43d681af1185 |
| Package manifest | 0849ada30219dea7df4aa34511d69a1a7ea1cb560602e4f0ed65de77538ac33a |
| Preparation seal | e4b4e3f3f6bc2dc2f9156a338d149219b0b79c46d07592e053d6d14b0345a5e1 |
| Qualification seal | a93fa65612977687ceaf2a9756ef9c65272e5ed401cec961acaa37dc050c3a71 |

Model: Qwen3.8-27B UD-IQ3_XXS. Runtime revision:
7e4c0a96880dae4fc4268ad441f8a6446bd5460a. Profile fixture revision:
b5ee42b47553c6882862665ca5a58dc0a921d8d0. Exact local launch paths remain in
ignored private-runtime records; their hashes verify. The portable command and
every effective setting are retained in the runtime-prepared chained record.

Selected configuration: q4_0 K/V, 56,576 context, 66/66 GPU layers, fitting off,
one slot, six threads, batch 256/microbatch 128, flash attention on, MTP disabled,
context shifting disabled. Native thinking on/xhigh, unlimited generation and
reasoning, seed 42, temperature 1, top-p .95, top-k 20, min-p 0, repeat penalty 1,
presence/frequency penalties 0. Client prompt-cache reuse is disabled and Q1's
actual cached-token counts are zero.

| Frozen request | Native and offline input tokens | Physical generation space | Completion status |
|---|---:|---:|---|
| Q1 | 36,096 | 20,480 | Correct normal response |
| Q2 | 412 | 56,164 | Withheld |
| Q3 | 20,565 | 36,011 | Withheld |
| D1 | 20,666 | 35,910 | Unexposed |
| D2 | 4,834 | 51,742 | Unexposed |
| D3 | 3,549 | 53,027 | Unexposed |
| D4 | 4,162 | 52,414 | Unexposed |

Q1 began at 12:28:44.901828 UTC and was received at 12:30:38.124402 UTC.
Elapsed invocation time: 113.218 s. Native prompt processing: 86.607 s at
416.78 tokens/s; generation: 26.528 s at 15.64 tokens/s. Endpoint usage is
36,096 prompt plus 416 combined output = 36,512 tokens. Separate offline text
counts are 368 thinking and 45 final tokens; these are retokenized text, not
original generated-token segmentation, and must not replace endpoint usage.

Independent [verification](VERIFICATION.json) checks all 46 package files,
43 execution-source identities, 17 public files and six local private files
across the two sealed stages, and all 19 chained records. All seven native
input counts match the pinned offline tokenizer. Exact separated outputs match
the raw reply. The verifier is saved as [verify_evidence.py](verify_evidence.py)
and makes no model-server calls; its hash is in the report. It accepts local
model/tokenizer paths and a new output path to reproduce the checks.

Fifteen selected interface tests passed before live exposure with Python 3.12:
PYTHONPATH=src; unittest discover -s tests -p test_interface*.py -v.
They cover the existing interface and new runner's isolation, configuration,
custody, nonexecution, transport/memory stops and direct-review requirement.
This is a focused test run, not a full-suite or historical-experiment rerun.

