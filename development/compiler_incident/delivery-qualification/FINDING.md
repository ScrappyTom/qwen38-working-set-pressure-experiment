# Full retained history prevents usable evidence delivery at the sampled states

The offline qualification reproduced all four recorded native input counts and
measured exact, reviewer-selected retention alternatives with the pinned tokenizer.
Keeping the newest result is already too large at both sampled omissions. A
protected working group that also retains that result cannot fit those states
at 16k. The supplemental measurement below distinguishes changing approach and
releasing that unrelated result; some local work then fits.
The completed run, its scores and its sources remain unchanged. No model
completion or operating-host change occurred in this qualification.

| Next decision | Recorded all-external input | Newest event payloads | Local repair plus newest | BUILD-A report entry plus newest | Both report entries plus newest |
|---|---:|---:|---:|---:|---:|
| C01 X023 | 13,424 | 16,950 | 17,481 | 20,906 | 24,430 |
| C02 X021 | 12,688 | 16,214 | 16,745 | 20,171 | 23,695 |
| C01 X030, withheld | 16,445 | 16,453 | 16,984 | 23,943 | 27,467 |
| C02 X029, withheld | 16,154 | 16,158 | 16,689 | 23,637 | 27,161 |

The local repair set contains the acquired README and current unary source. A
report-entry set contains the acquired README, exact current report placeholder,
original capture and BUILD-A capture; the two-entry set also includes BUILD-B.
Every set includes the newest result. These are plausible assisted sets, not
unique minimum requirements or a model-selected plan. Keeping the newest result
can include material unnecessary for a subsequently changed approach. The probes
do not establish which group Qwen would choose, whether a smaller operation would
suffice, or whether it would complete a contribution.

“Newest” restores the event's existing action-payload and result-body records
together. The two sampled omissions concern retrievals, whose payload is the
returned result. At C01 X030 the rejected patch's error already belongs to retained
signal; the extra payload is its proposed old/new text. Its 16,453 figure is not
a claim that delivering the error itself requires those extra fields. The
unchanged all-external history already exceeds 16k there.

## Supplement: permit a changed approach to release unrelated material

The proposed operating rule allows Qwen to change its approach. The initial
probes' requirement to keep the newest result is stricter than that rule. A
separately preserved [supplement](offline-002-groups-alone/MEASUREMENTS.json)
therefore measures each same assisted group without automatically adding the
newest event. It reuses the qualified rendering and selection code; it changes
neither the original run nor the first qualification.

The local repair's README and current unary source fit at **13,948 / 13,212**
tokens in the two omission states. The newest original capture is excluded in
both, so this does not establish delivery of that requested capture. It does
show that these states do not make every useful contribution impossible.
The report-A group still requires **20,906 / 20,171** tokens, because it needs
the original capture. Both final denied states remain above 16k even for the
local repair group alone (**16,969 / 16,678**).

Twelve additional group measurements were made with the pinned offline tokenizer.
Some reproduce identical texts from the first qualification; they are not twelve
independent scenarios. This supplements the recommendation: distinguish the
evidence required for a chosen contribution from an unconditional newest-body
retention rule. It does not prove that Qwen will choose or finish that contribution,
or that shorter trajectories remove the need to manage long accumulated history.

Nonprefix retention cannot truthfully retain the old prefix counter. The derived
measurement schema replaces it with an explicit sequence list and recomputes
verification. Its all-external form costs six fewer tokens in each case; the
table's first column remains the actual recorded input. All other state, event
signals, guards, identities, task and tool descriptions remain exact. These
derived views were never sent to Qwen and are not an adopted interface.

## Where the space goes

Removing the complete event frame and its verification for cost measurement
leaves 3,544–3,545 tokens. Their marginal input cost is 9,879 and 9,143 tokens at
the sampled omissions, and 12,901 and 12,610 at the final denials. Removing the
system-message content instead saves 2,070 tokens in each state. These separate
ablations are deliberately nonexecutable: removing a component does not qualify
a truthful replacement, and marginal token counts need not be additive.

This earns examining a more compact decision view while retaining full custody.
It does not yet select which history should be shown, which records Qwen needs
for a contribution, or how it should request related evidence. An earlier stop
would avoid futile acquisition but would not demonstrate successful recovery.
The tool reference contains required operating information; deleting it to gain
space would reintroduce an already diagnosed omission.

The 23,808 column limit is only an input admission ceiling. For example, the
23,695-token two-entry probe leaves 32,881 physical tokens, above the old planning
reserve but below the 38,037 generated tokens in the context-exhausted resident
response. Fitting this input does not qualify uncapped generation to finish.

## Verification and limits

All 1,570 original public evidence files and 71 frozen source pins were checked
before and after measurement. Thirty-two distinct native texts were counted
offline, using the saved two-message template envelope. Every original native
count agrees with its recorded tokenizer output. The derived requests/native
texts, material/event selections, counts and hashes are preserved in
[offline-001](offline-001/MEASUREMENTS.json), with its own byte inventory.

Six focused checks pass against actual tool operations: nonprefix body delivery
with unchanged signals; current versus unchanged-file applicability; escaped
whole-line reads through storage/retrieval/next-input inclusion; a rejected patch
without mutation; corrupt or missing evidence rejection; and native-envelope
validation. The escaped return check qualifies exact construction/inclusion and
the 22,000-byte result bound, not a general 16k admission guarantee for every
possible escaped source. There was no new full-suite run or model inference.

The original complete transcripts were directly reviewed before these probes.
C02 X021 recognizes missing content correctly; its absence is visible in the
actual input. The separate resident failure still shows that available evidence
alone does not ensure a finished action. No single diagnosis explains both.

The next bounded step is the [Qwen consultation](../../delivery_dialogue/SPEC.md)
on the actual historical input and what one contribution requires. Save its
first interpretation before giving these source-checked capacity facts. Only
then choose a prospective view/retention change, if one is earned. A completed
contribution and continuation from saved work remain the subsequent behavioral
tests; no new pressure run or memory feature is implied by these measurements.
