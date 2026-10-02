# Bounded runtime screen and RAM observation

The four-measurement target was not completed. Two representative inputs returned
complete endpoint responses; the third exhausted the remaining fifteen-minute
apparatus window during input processing. No fourth request was sent. There were
no behavioral operations. Preserve `apparatus_qualification/run-001` unchanged as
`stopped_preserved`, not a passed four-repeat qualification.

The saved-only verifier authenticates 20 artifacts, 1,231 source bindings, 15
custody records, all three actual requests, both full responses, native equality
with the prepared inputs, and normal monitor/server closure. The timed-out third
request has zero returned endpoint bytes; its complete timing and generation are
unknown. Both complete responses contain only the deliberately capped beginning
of reasoning. Neither is a task action or action-completion result.

| Input | Input tokens | Prompt seconds | Prompt tokens/second | Generation seconds | Request seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unchanged seven sources, P01 | 21,608 | 456.756 | 47.308 | 2.269 | 459.094 |
| Released six sources, P02 | 11,723 | 246.260 | 47.604 | 2.036 | 248.860 |

Each generated 32 tokens and reported zero reused prompt tokens. Slow input
processing is reproduced in both representative inputs under the unchanged
runtime. These are descriptive samples, not a repeated throughput comparison or
evidence that release improves completed-task performance. Earlier 407--418
tokens/second measurements and the recent 36--44 range remain historical
comparators with an unresolved cause.

The observed server RAM is substantial: resident working set ranges from
10.010 to 11.758 GiB; private bytes range from 12.098 to 13.951 GiB. Windows
reports owned GPU dedicated allocations up to 11,214 MiB and shared allocations
from 162 to 324 MiB. These counters describe allocations, not whether particular
weights or computations spilled. NVIDIA's separate free-VRAM minimum is 88 MiB;
the accepted advisory-margin policy is unchanged. System available memory stays
above 29.1 GiB in the samples. Missing counters are not substituted with zeros.

The actual launch reports 66/66 layers assigned to GPU, a 9,685.21 MiB CUDA model
buffer and a 397.85 MiB CPU-mapped model buffer. It also reports a RAM prompt
cache and recurrent context checkpoints of 149.626 MiB each; one saved prompt
cache entry is reported as 979.291 MiB. Zero reused input tokens does not mean
the server stores no RAM cache. Those receipts identify host-side allocations;
they do not establish the cause of all RAM use or slow prefill. No observed CUDA
failure, context truncation, driver change, CPU-offload setting, or model-policy
change occurred.

After the owner's Blender warning, direct inspection found two background Blender
jobs. The character script sets Cycles CPU at its render sites; the props script
uses the common kit, whose lighting/render setup also sets Cycles CPU. Neither
Blender PID appears in the sampled GPU-memory rows. Windows' desktop compositor
is the largest sampled non-Qwen allocation, about 0.83 GiB. The saved
`BLENDER-CPU-CHECK-001.json` contains source settings, hashes, command lines and
the sampled inventory. This is a source-and-counter check, not a captured Blender
render-device receipt or proof that concurrent CPU work has no performance cost.
No Blender process or setting was changed. Slow P01 processing began before the
two observed Blender processes were created.

## Preparation-process limitation and next boundary

At the measured rate, A/B/B/A requires roughly 1,408 request seconds even without
measurement overhead. The fifteen-minute screen therefore could not complete its
planned repeats. The controller's four-complete-response gate turns that apparatus
budget mismatch into a blocker for behavior. It does not establish runtime
instability; it also does not qualify repeated stability. Record this as our
preparation-policy limitation rather than another Qwen failure.

The scoped recommendation is to retain the stopped screen and accept its two
complete representative measurements as descriptive apparatus evidence. Declare
that reduced evidential basis before behavior, keep repeatability and cause open,
and make no causal speed claim. Do not extend this screen, silently change its
result, tune the driver, or spend another four calls seeking a favorable number.

A prospective successor preparation must enforce that exact exception rather
than bypass the old gate: authentic full P01/P02 inputs and responses; the third
stop at the declared deadline; no observed CUDA/truncation failure; complete
custody, telemetry and owned closure; unchanged actor policy and initial wires.
Any other failure still blocks. Preserve the original preparations and requalify
both under version 002 before their one uncoached attempt each. No behavioral
request, task, account, source selection, checker or opportunity is changed.

This record is not a hardware diagnosis. The next informative result remains the
completed contribution after the controlled information transition.
