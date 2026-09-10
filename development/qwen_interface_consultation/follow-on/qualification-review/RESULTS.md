# Follow-on qualification: stopped after Q1

The September 10 q4_0/56,576 attempt does not qualify the four design calls.
Q1 returned all four retention fields correctly, but whole-device free GPU
memory reached 339 MiB against the frozen 350 MiB minimum. The runner preserved
the normally completed answer, withheld Q2/Q3, shut down its server, and sealed
the partial attempt. No design request was sent and no Qwen design preference
was obtained. The six remaining requests are unexposed, not failed answers.

| Observation | Result |
|---|---|
| Completion requests sent / received / completed | 1 / 1 / 1 |
| Q1 content | Four correct fields, normal stop |
| Q1 prompt / generated output | 36,096 / 416 tokens |
| Generation space before / after Q1 | 20,480 / 20,064 tokens |
| Q1 elapsed time | 113.218 seconds |
| Load/tokenization minimum free memory | 563 MiB |
| Inference-stage minimum free memory | 339 MiB; 544 of 584 samples below 350 |
| Q2, Q3, D1–D4 | Withheld; zero completions |
| Truncation, CUDA error, retry, executed tool | None observed |

The low samples span 06:28:45.920–06:30:37.968 local time, about 112 seconds.
This is a sustained shortfall during the request, not just an isolated sample.
Memory is measured for the whole GPU, so this record does not identify the
allocation or process responsible for every MiB. Correct simple retention and
successful loading do not establish suitability for long reasoning. Q2/Q3
remain untested, and Q1's inert padding supplies no continuity evidence.

The [direct transcript audit](DIRECT_TRANSCRIPT_AUDIT.md) covers the complete
exposed input, separate thinking, final JSON, and following host decision.
[Independent verification](VERIFICATION.json) checks 46 package files, 43 source
identities, both stage seals and all 19 chained records, including local private
runtime files. All seven native input counts match offline tokenization. See
the [execution receipt](EXECUTION_RECEIPT.md), [host audit](HOST_PATH_AUDIT.md),
and [apparatus finding](APPARATUS_FINDING.md) for scope and limits.

Retain the measurement repairs and the initial consultation findings. Complete
visible tool requirements remain mandatory in a new interface, and their
presentation remains the preferred first narrow comparison. The current
prepared consultation supplies those requirements as facts, but the design
stage was not reached. No host metadata refactor, preference-based naming
choice, matched comparison, or fresh investigation has occurred here.

The [prospective capacity revision](../CAPACITY_REVISION.md) recommends
q4_0/49,152 for a separate qualification, retaining uncapped xhigh thinking and
the 20,480-token development reserve. It is a concrete proposal, not a qualified
preset or permission to restart this consumed attempt. Preserve the original
q8 evidence, the old q8 design package, this q4 package, and this failure.

Fifteen focused interface tests passed before exposure. That is not a full-suite
result or a rerun of the historical experiments. The later sixteen-response
signature comparison remains to be prepared after an actual design consultation.

