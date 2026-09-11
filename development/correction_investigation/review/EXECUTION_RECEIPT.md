# Execution receipt: receipt corrections R01

The owner-approved single run completed on 2026-09-11 with a checked submission.
R01 used seed 32452843 and 14 of its frozen 24 completion/action calls. Every
request received one complete response and executed one accepted action. No
retry, replacement, intervention or extra model conversation occurred.

## Identities and custody

- Execution base commit: 0ab8ad78c5c7e32bede9a304c13d87d0405cb0a9.
- Prepared package: f8eabbcbd87e9dd296ebf41448a7c9e9d32fed01f54d59b1ce593d52260ef33c.
- Response seal: 1f3d4c1c5199ca4b4f9b31d3ade4d4d2494c8fc25d60fa9afc47bd79aba05c4d.
- Initial candidate: cb2c2d7e160c4c829b71ae1a033d34e1416224bfab84d57477857c94a731f349.
- Submitted candidate: 3dce94985b28ebdae35c0bbf6be4d7db639503dc8319a32ffbe8727431e602b1.

[Offline verification](VERIFICATION.json) checks 202 sealed public files, 133
chained records, 71 pinned source/task/test identities, three local-only runtime
files and 15 canonical payload files. It reconstructs all 14 API/native inputs,
independently recounts 42 distinct input/thinking/final texts with the pinned CLI
tokenizer, and replays all 14 actions through the actual executor. Results,
candidate/session states, check opportunity and next-turn decisions match exactly.
It makes zero completion requests and is not a second implementation of host
semantics or a substitute for direct reading.

Direct review read the initial native input in full, every changed field and
appended event in each following actual input, all complete thinking and final
fields, every result, the next decisions and final candidate. Exact comparison
also verified the unchanged system/settings and native inclusion of each actual
user state. All 13 nonterminal results entered the next sent input. Submission
has a saved result and terminal decision, with no subsequent model request.

The sole patch follows complete exact acquisition of totals.py at action 7.
All 38 public cases passed at action 13 and replayed identically. Only totals.py
changes; direct final-source review confirms each signed contribution uses its
own receipt's depot/item. The eleven focused mocked checks passed during
preparation; this execution/review does not claim a new full-suite test run.
Consumed source and preparation bytes remain unchanged.

## Runtime and accounting

Qwen3.8-27B UD-IQ3_XXS and llama.cpp b10434 retain the pinned identities in
verification: q4_0 K/V, 56,576 physical context, no MTP, full offload, fit off,
one slot, uncapped native thinking/xhigh, all four generation budgets -1.
Temperature 1, top-p .95, top-k 20, min-p 0, repeat penalty 1 and frequency/
presence penalties 0 remain fixed. Prompt caching is off. The native prefix
explicitly requests careful validation and consideration of plausible alternatives.

P <= 23,808 preserves G=32,768 as planning room, not an output cap. Actual P grows
from 3,170 to 13,588; maximum input plus output is 13,791, leaving at least
42,785 physical tokens after generation. No capacity denial or pressure boundary
occurs. Cumulative input is 100,163; generated output is 13,348. Separately
retokenized saved thinking/final text is 12,652/654 tokens; those are text counts,
not original generated-token segmentation.

Model-request time totals 918.847 seconds (15.31 minutes); task-loop wall time is
928.469 seconds (15.47 minutes). Recorded response processing totals 1.108
seconds. Request time excludes later tool execution and is not whole-task time.

Telemetry has 4,523 samples, a maximum .224-second sampling gap and minimum
free GPU memory of 321 MiB under the accepted advisory policy. The 11,773 MiB
maximum includes shutdown and is not inference headroom. All pre/post checks
retain the selected runtime, with no CUDA error, truncation or runtime metadata
mismatch. The owned server and monitor closed; the dedicated port was free.
