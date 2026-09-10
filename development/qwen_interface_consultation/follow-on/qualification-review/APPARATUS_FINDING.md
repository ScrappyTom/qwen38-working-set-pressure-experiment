# Apparatus finding: generation space did not establish GPU reserve

The native input ceiling and output space were measured correctly. Q1 fills
36,096 input tokens and leaves the planned 20,480 for generation. The largest
prepared design input uses 20,666 tokens, leaving 35,910. Q1 normally generates
416 tokens and has 20,064 remaining afterward. There is no observed context
truncation or CUDA failure.

Nevertheless, q4_0/56,576 leaves only 339 MiB sampled free during this inference,
11 MiB below the specified minimum. The earlier 563 MiB load/tokenization margin
was insufficient evidence for live dispatch beyond qualification. Passing a
simple retention question does not waive the hardware criterion or exercise the
long reasoning that the follow-on was meant to accommodate. The design decision
is therefore withheld even though the sole exposed answer is correct.

This is a valid partial development record. It is not a completed three-call
qualification, a four-call design consultation, a q4-versus-q8 quality comparison,
or a test of independent investigation. The codes and arithmetic come from a
reused profile fixture. Its deliberately inert fill tests input capacity and
retention only; it supplies no authentic continuity evidence. Q2/Q3 have no
outcomes, and a 416-token answer cannot validate the entire uncapped reserve.

Whole-device telemetry and finite sampling limit attribution. A smaller KV
allocation is a justified next preparation candidate, but memory recovered by
reducing context must be measured during the same classes of workload. Do not
lower the 350 MiB criterion, truncate thinking, silently switch a remaining
request to a new preset, or relabel a replacement as part of this attempt.

Historical Experiment 020 results, measurement repairs, initial q8 consultation,
and its interface-friction findings remain intact. The next narrow interface
question remains how Qwen prefers complete tool information to be presented.
No new preference or adopted presentation is inferred from this capacity probe.

