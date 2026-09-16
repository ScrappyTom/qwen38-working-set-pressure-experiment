# Attempt stopped for a reproduced recovery-inspection defect

Freeze 2b95ca36 produced two complete uncoached responses and three operations. It
closed through a graceful operator stop, with no file changes, check or submission.
Twenty-two requests and 69 operations remain unused in this closed attempt.

| Call | Input | Generated | Request seconds | Actual effect |
|---|---:|---:|---:|---|
| C01 | 6,656 | 866 | 58.469 | Small source read rejected by host |
| C02 | 23,659 | 6,946 | 471.813 | Account saved; ambiguous patch rejected |

Total model-request time is 530.282 seconds (8.838 minutes); task-loop time is 548.750
seconds. Peak input plus output is 30,605 of 56,576. Minimum sampled free GPU memory
is 192 MiB under the existing advisory policy; no runtime failure is observed.

The corrected match addresses help C01 identify a real information need. The host
then revives hidden bulk and counts the requested excerpt twice, rejecting even its
one-line trial. C02 displays the sought source despite that rejection but drops the
previous ambiguity diagnostic. Qwen then guesses that a slightly longer anchor is
unique. The guard correctly rejects it. See the full transcript, host and artifact
audits; no one cause is assigned to all deliberation.

Exact replay verifies two replies, twelve native inputs, 118 custody records and 361
source identities without inference or check re-execution. The source/checker/policy
freeze is preserved. Standing owner authorization covers the next separately frozen
recovery-inspection repair and continuation, not rewriting this failure as success.
