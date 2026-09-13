# Apparatus finding

VERIFICATION.json independently checks twelve sealed files, ten chained records,
53 pinned source identities, exact request/native/tokenization and extracted raw
response fields, runtime closure, cache-off and usage. Three ignored private
runtime files were locally verified against their recorded hashes. The verifier
ran on the frozen D1 sources at 0fa8ca96 before prospective source edits.

The 23,114-token input leaves 33,462 tokens in physical context 56,576, above the
selected prospective generation reserve of 32,768. The reserve is not a cap.
Qwen used 25,851 generated tokens and finished with a final answer. The shared
nonexecuting helper also emits an older reserve field; selected_generation_measurement
and this report use the declared 32,768 setting, not that helper default.

GPU sampling reached 242 MiB free across 8,379 samples. This is a lower observed
margin than earlier development calls, not a pass of the historical 350 MiB
target. It is covered by the owner's accepted monitored advisory policy. There
was no observed CUDA failure or incomplete response. No setting or threshold was
changed during this request; this does not qualify every future workload.
