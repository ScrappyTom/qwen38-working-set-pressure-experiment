# Proposed next capacity qualification

The [sealed q4/56,576 attempt](qualification-review/RESULTS.md) is consumed.
It returned one correct retention answer but missed the 350 MiB GPU minimum.
Q2/Q3 and all design calls remain unexposed. This proposal does not resume or
replace that record. No revised completion or runtime launch has occurred.

Recommend **q4_0 K/V at 49,152 physical context** for a separately identified
qualification, retaining the same pinned model/runtime, full GPU offload,
MTP disabled, native thinking on/xhigh, uncapped output, sampler and seed 42.
Keep the development generation reserve at 20,480 and the GPU minimum at
350 MiB. The resulting input ceiling is 28,672 tokens. This is a temporary
development capacity choice; the owner's primary q8/32,768 configuration and
the future approximately 25k pressure study remain separate decisions.

Why this candidate: the measured native q4 KV buffer was 994.50 MiB for 56,576
cells. Its linear per-cell component predicts 864.00 MiB at 49,152, a reduction
of 130.50 MiB. Adding that difference to the observed 339 MiB suggests about
469.5 MiB free if every other allocation stays equal. This is an estimate, not
a qualified memory margin. It leaves more room than a small reduction to
55,296, whose same calculation saves only 22.50 MiB and predicts 361.5 MiB free.
Dynamic allocations, desktop GPU load and later reasoning still require live
measurement; these calculations do not justify assuming a pass.

The largest current design input is 20,666 tokens. At 49,152 it would have
28,486 generation tokens, 8,006 beyond the retained reserve. Q3 would have
28,587. Existing Q2/Q3/D1–D4 request contents can remain byte-identical after
confirming the native template; none has received a response. Reconstruct Q1
prospectively to the largest native input at or below 28,672, preserving the
same pinned codes/arithmetic fixture. Save the selected and next-size counts.
Do not reuse the oversized 36,096-token Q1 or present its answer as the new
qualification. Reused fixture material remains development evidence.

Before any exposure, retain an exact copy of the consumed runner, prepare a
separate package and output locations, and freeze the revised context identity,
all seven exact requests, native render/counts, expectations, source identity,
and call ceiling. The implementation change is limited to the explicit context
selection and corresponding runtime verification; no host, tool schema,
comparison variant or memory architecture change belongs in this revision.
The present runner and consumed package remain unchanged by this proposal.

Requested live scope for that revision is three qualification completions once,
followed by four design completions only if qualification passes and all five
existing audit products support continuing. Preserve the same Q1–Q3 then D1–D4
order, fresh sessions, no cached prompt reuse, nonexecuting replies, memory
sampling, direct transcript review, and stop/no-retry rules. A failure is kept
as another separately identified development result. No live sixteen-response
comparison or fresh investigation is included.

The current authorization froze one attempt per request and prohibited preset
switches or retries. A newly allocated three-plus-four attempt needs an explicit
owner execution decision; six unused requests are not transferable permission
to change their qualification configuration. This is the existing experiment
boundary, not a new approval framework. Approval can cover qualification and
the conditional design stage together, without another question between them.

After successful design review, record Qwen's original suggestions and select
at most one concrete presentation variant. Complete visible tool signatures
remain the preferred first change. Prepare its sixteen-call matched comparison
for the later execution decision, count added input cost, and keep object-scope,
resource wording and navigation alternatives in the existing decision record.
