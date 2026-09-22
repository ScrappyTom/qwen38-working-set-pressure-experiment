# Shift run-001: apparatus cost audit

22 September 2026. Read-only audit of the closed attempt frozen at `795fb292`.
No model, native sizing endpoint, runtime, checker, test or profiling run was
started for this audit. Original inputs, outputs, observations and run records
remain unchanged.

The existing timing claims stand. The 100.871 seconds outside model-request and
reply-processing timers are predominantly identifiable **runner intervals**:
post-response validation and pre-dispatch work. Full source verification occurs
in both. The saved records do not time hashing separately from the other work,
so they do not establish an exact source-verification cost or an optimization
benefit.

## Timer boundaries

| Recorded monotonic timer | Seconds | What it includes |
|---|---:|---|
| Task loop | 819.594 | Initial snapshot, input preparation, all fourteen invocations and their processing, final snapshot |
| Model requests | 639.251 | HTTP completion requests, including transport; not only generation |
| Reply processing | 79.472 | Requested operations, saved operation/state records, and preparation of resulting inputs |
| Arithmetic difference | 100.871 | Work outside the two inner timers but within the task loop |

`scripts/run_uncoached_contribution.py` starts the request timer immediately
before posting the completion request and stops it when the response returns.
It then preserves and validates the response, verifies the source package,
checks runtime health, decodes the final reply and records `reply_selected`.
Only then does the reply-processing timer begin. Thus reply processing is not a
timer for everything the host does after receiving a response.

The processing timer includes `process_reply`, operation/state recording and
`measure` of the following state. On a cache miss, `scripts/run_bounded_parser.py`
verifies sources and runtime health **before** it records `input_constructed`,
then performs native rendering/tokenization and records the prepared wire input.
Pre-dispatch source verification and health checking also occur before each
`invocation_started` record and outside the request timer.

## Where the difference appears in saved timestamps

These are differences between the records' UTC timestamps, not new measurements
or separately instrumented function costs. Values are rounded for display.

| Nonoverlapping interval within the task loop | Count | Seconds | Supported interpretation |
|---|---:|---:|---|
| `response_received` to `reply_selected` | 14 | 48.435 | Response preservation/extraction, validation, full source verification, runtime health, reply decoding and recording |
| Previous `invocation_completed` to next `invocation_started` | 13 | 45.431 | Next-invocation setup, cached-input lookup/validation, full source verification, delivery/accounting and health/dispatch recording |
| Starting `contribution_feedback_saved` to first `invocation_started` | 1 | 6.842 | First native input preparation and first dispatch, including source verification at both boundaries |
| Last `invocation_completed` to `task_loop_completed` | 1 | 0.014 | Final snapshot/closure bookkeeping within the loop |
| Remaining arithmetic difference | — | 0.150 | Not separable from clock/timer/record boundaries and other unmeasured work |

The first four intervals total 100.721119 seconds. Subtracting them from the
100.87099999992643-second monotonic-timer difference leaves 0.14988099992643
seconds. The instruments do not share exactly the same boundaries: for example,
the UTC invocation-start-to-response intervals total 639.323023 seconds, while
the enclosed request timers total 639.251 seconds. UTC reply-selection-to-processed
intervals total 79.513265 seconds, versus 79.472 seconds in the enclosed timers.
Initial snapshot work precedes the first interval above. Logging, persistence,
timer reads and clock precision also straddle boundaries. The small remainder
is therefore not an independently measured activity.

Post-response intervals range from 3.386 to 3.606 seconds; between-call intervals
range from 3.333 to 4.220 seconds. Within the post-response total, the interval
from `response_extracted` to `post_response_runtime_check` alone totals 48.205426
seconds. The code places full package verification and health checking there,
with token/finish validation and record overhead. This locates the repeated
cost, but does not divide it into hashing, filesystem access, health parsing or
other execution time.

## What the apparatus actually repeats

The execution manifest binds 1,122 source/prerequisite files. The normal executed
code path invokes its full `verify_sources` callback:

- once for each of the 23 uncached native input measurements;
- once before each of the 14 completion dispatches;
- once after each of the 14 complete responses.

That is 51 full verification passes within this task loop, or 57,222 per-file
hash checks by count. `scripts/bounded_parser.py:verify_sources` iterates the
manifest, and `src/working_set_exp/jsonutil.py:sha256_file` opens and reads each
file; it does not reuse a prior digest. This inventory includes qualification
evidence as well as executable source. These are call/count facts derived from
the saved sequence and the frozen implementation, **not measured CPU or disk
time**. Operating-system caching is not measured.

Twenty-two native measurements occur during reply processing and the initial
one before the first dispatch. Consequently, repeated verification also contributes
to the 79.472-second processing category, not only to the 100.871-second difference.
Calling the former entirely tool-execution cost would also be inaccurate.

## Native sizing and the actual check

The 23 saved native measurements contain 46 endpoint exchanges. Their logged
request-to-response UTC intervals total:

| Endpoint | Exchanges | Seconds |
|---|---:|---:|
| `/apply-template` | 23 | 0.447594 |
| `/tokenize` | 23 | 0.722956 |
| Combined | 46 | 1.170550 |

These spans include endpoint transport and record-boundary work; they are not
isolated server computation. The broader `input_constructed` to
`wire_input_prepared` intervals total 1.822057 seconds, including those exchanges,
render validation, encoding and saved artifacts. They exclude the source and
health checks performed before `input_constructed`. The initial interval accounts
for 0.098039 seconds; the remaining 1.724018 seconds are already within reply
processing and must not be added to task-loop cost again.

The one actual public check has a preserved observation start of
`2026-09-22T18:06:52.909967+00:00` and completion of
`2026-09-22T18:06:53.066936+00:00`: a 0.156969-second observation interval. It
captured all 2,546 stdout bytes and zero stderr bytes, with exit zero. C13's
reply-processing timer is 4.047 seconds and also includes operation bookkeeping,
observation preservation and the next input's preparation. The observation
interval must not be equated with all check-related host work. No check was
re-executed to obtain these figures.

## Setup, closure and limits

The saved interval from `attempt_reserved` to `runtime_ready` is 29.220835 seconds.
The interval from `task_loop_completed` to `runtime_closed` is 2.130473 seconds.
Both lie outside the reported task-loop timer. Package verification precedes
`attempt_reserved`; final inventory/seal generation follows runtime closure.
Neither has a complete separately logged duration here. Preparation, human/agent
review and publication are additional costs outside this run's loop.

This audit establishes that a material part of the non-model time belongs to the
evaluation apparatus and its repeated integrity/health work. It does not establish
that any particular verification is unnecessary, what removing it would save,
or that this overhead generalizes to other workloads. The current record is
adequate to locate the composite costs, not to select or validate an optimization.
No source, timing policy or subsequent run configuration is changed by this audit.

## Evidence and reproduction boundary

Calculations use `run-001/records.jsonl`, grouping the named record types in
sequence order and subtracting their `created_at_utc` values; inner timer totals
use `response_received.payload.elapsed_seconds` and
`reply_processed.payload.processing_seconds`. The task total comes from
`task_loop_completed.payload.task_loop_seconds`. The actual checker interval
comes from `observations/CHK-0021/outcome.json`.

The manifest, custody-log file and observation were checked against their size
and SHA-256 entries in the original `RESPONSE_SEAL.json`:

- Manifest: `3e2654931ebe20705c5eb1e4ccf5a2c14d06667dd7c7789bf3e201e3e09ce6eb`.
- Records: `1483e9bf34935a3fdffcf17d1b2046b893306889a6feae3921ead395daf5b1cc`.
- Check outcome: `b429b79bfc39bc3469fdbde1faef5ea445702a7b0e4abab66edc9bdae49a2cc4`.

The inspected current copies of `run_uncoached_contribution.py`,
`run_bounded_parser.py`, `bounded_parser.py`, `prepare_investigation_loop.py`
and `jsonutil.py` match their run-manifest hashes. Their relevant boundaries are
`Loop.invoke`/`Loop.execute`/`run_once`, inherited `Loop.measure`, `verify_sources`,
`health` and `sha256_file`. This is a focused timing/source audit, not a new full
evidence-seal verification or a rerun of the previously completed exact replay.
