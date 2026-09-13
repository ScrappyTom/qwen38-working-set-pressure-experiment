# Revised priority: host capacity and useful work

The owner challenged the recommendation to retain the 512-character patch limit
and ask Qwen to work around it while trying smaller source pages. Codex withdraws
that recommendation. Establishing that a shorter anchor or a two-action sequence
exists does not establish that the interface is economical or suitable for the
work. This prospectively supersedes the next-step recommendation in
`configparser_follow_up/review/DECISION.json`; that historical record and all
completed evidence remain unchanged. No implementation or model run occurs in
this revision.

The follow-up used 48,494 generated tokens and 49.510 request minutes. Direct
review found repeated fragment counting and answer rehearsal as well as useful
interpretation. We cannot assign all that cost to the cap, but another model
conversation is unnecessary to establish that exact size arithmetic belongs in
the host. The reviewer-built 420-character alternative was evidence of
expressibility, not a reason to preserve the burden.

Source inspection identifies two different host responsibilities:

- `action_schema` restricts each patch fragment to 512 characters. The executor
  separately allows 2,000 UTF-8 bytes per fragment, 5,000 bytes per serialized
  action and a 6,000-byte effective diff. These are different bounds; none is a
  direct measurement of the model's remaining context. Raising only the grammar
  limit would still leave escaping, byte limits and returned feedback to qualify.
- `_read` fits whole lines within 18,000 source bytes and both 22,000-byte return
  and exact-recovery bounds. It does not size that page against the complete next
  model input. `select_input` then removes an oldest prefix of payloads while
  retaining every event's signal. The delivery gate correctly stops when the
  newest result is absent, but detecting the dead end does not prevent it.

The next preparation should address the working operation as a whole:

1. Let Qwen express an ordinary complete edit without manually counting or
   splitting it at an incidental character ceiling. Qualify a coherent action,
   patch and feedback allowance against actual library, test and documentation
   edits. Keep exact source/version guards and atomic application. The host must
   calculate sizes and report a truthful failure without committing partial work;
   it must not silently shorten a proposed edit. Do not merely substitute another
   arbitrary small cap.
2. Make read admission account for the complete next input, including useful
   supporting evidence, the current edit target and immediate feedback. Qualify
   retaining a declared working group through an edit/check cycle. Smaller exact
   pages are one implementation technique, not the objective and not a numeric
   packing problem to hand to Qwen. Budget resident history too: shrinking bodies
   alone cannot solve the growth of all retained event metadata.
3. When the useful group cannot fit, narrow the inspection or use bounded
   extraction with exact source support. Choosing relevant evidence still needs
   reasoning; deterministic tokenization does not supply that judgment. Start
   with the existing exact sources, saved results and version bindings. Assess
   any model-selected group or extracted finding by whether it supports the next
   actual edit and check, including omitted qualifications and helper-call cost.
4. Use the unfinished regressions/documentation contribution as the concrete
   target. First qualify the complete delivery and mutation paths offline, then
   assess Qwen completing checked saved work and continuing from it. Assisted
   source groups are capacity examples, not evidence of autonomous selection.
   Judge complete contributions, regressions, repeated acquisition and total
   processing rather than accepted actions or shorter thinking alone.

The existing result-access path already retrieves evidence independently of
earlier thinking; keep it. No replacement database or new vocabulary study is
selected. Qwen remains a development partner for consequential interpretation
issues, not an arithmetic service. The present q4/56,576, no-MTP, xhigh/uncapped
settings remain the preparation baseline; input and generation accounting must
stay explicit. Completed attempts are not reopened, and a future implementation
must be qualified before exposure. This is a changed engineering priority, not
an unchanged replication or a claim that working-group retention is proven.
