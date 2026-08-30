# Experiment 017 Direct Transcript Audit

## Audit identity and scope

- reviewer: Codex primary project agent
- mode: condition-aware, post-seal corrective/direct review
- actor: Qwen3.8-27B AD-IQ2_S
- reasoning: private, server-capped at 512 tokens, omitted from later history
- sampler/seeds: frozen runtime profile; seeds 173205 and 223607
- coverage: all 21 completed live calls across all six branches

The exact artifact index is `TRANSCRIPT_INDEX.json`. The review below is based
on the saved model-facing request state, private reasoning, strict JSON action,
tool result, next request, and terminal candidate—not branch summaries alone.

## What the actor actually saw

Each reconstructed request contained one monotonically sequenced event frame.
For every historical event, it retained the action type, readable target,
acceptance/status, exact candidate/file/check bindings, ranges or terminal
identity where applicable, and the names of exact fields available behind a
handle. Patch `old/new` strings and large result bodies were absent.

The request explicitly stated:

```text
handles = addresses for exact payload access; handles are not semantic evidence
```

This is important. `EVT-0001` alone would have been an opaque token. Qwen also
saw that it named an accepted patch on `archive/source.dat`, that `old/new`
were external, and which candidate transition resulted.

## Branch-level evidence

| Branch | What Qwen saw | What Qwen did | What the host did next | Interpretation |
|---|---|---|---|---|
| closure mint / 173205 | five completed events: observation reopen, target read, accepted patch, two complete required reads; current candidate visible | reasoned that only check and submit remained; did exactly that | current check passed; submission accepted | resident progress was sufficient; no bulky payload reopened |
| closure mint / 223607 | same five completed events and bindings | reopened the old observation result, reread the already-patched two-line file, then checked/submitted | all accepted | Qwen understood the signal but chose extra exact confirmation; handles can invite verification, not only save context |
| stale sable / 173205 | predecessor check pass, later accepted patch to a new candidate, two complete reads | explicitly classified the old pass as predecessor-bound; checked current candidate and submitted | current check passed; submission accepted | binding signal, not check stdout body, carried validity |
| stale sable / 223607 | same stale/current structure | same current-check then submit path | accepted | replicated candidate-bound check interpretation |
| historical signal / 173205 | accepted patch on `archive/source.dat`; `old/new` absent but available at `EVT-0001`; marker absent from prompt | reopened the event, extracted `ARCHIVE-Z7`, read `report.py`, formed the correct patch, mistyped the candidate hash, corrected it after rejection, checked/submitted | exact payload returned; stale binding rejected; corrected patch/check/submit accepted | signal directed exact demand-loading; one opaque-ID transcription error consumed all six calls but did not change quality |
| historical signal / 223607 | same event signal; marker absent | reopened event, extracted `ARCHIVE-Z7`, read, patched, checked, submitted | all accepted | clean five-call replication of the intended causal path |

## Private reasoning versus observable action

The reasoning/action alignment is strong in the two diagnostic branches.
Before the first action, both seeds enumerated the exact intended sequence:

```text
reopen event old/new
→ read report.py
→ patch with removed value
→ check
→ submit
```

Both then followed it. After reopening, both named the removed value as
`ARCHIVE-Z7`; after the current read, both specified the exact replacement.
The second seed executed that plan directly. The first seed's only divergence
was copying the current candidate hash incorrectly into the patch action. Its
next reasoning identified the stale-binding result, copied the exact resident
candidate, and retried the same already-derived patch.

The closure/stale-check branches likewise reasoned from the event sequence.
They enumerated completed obligations, compared check/candidate identities,
and moved to closure. The extra confirmation in closure seed 223607 was a model
policy choice visible in reasoning, not missing resident information.

## What the signal contributed

This run does not support “handles help.” It supports a narrower mechanism:

```text
readable event type/target/status/bindings
        ↓
model recognizes what exact fact is missing
        ↓
handle provides exact low-arity access
        ↓
model interprets the body and acts
```

In the historical case, the marker was absent before access and both seeds
opened exactly the advertised action payload. In the closure and stale-check
cases, the exact payload was not necessary to decide the next obligation, and
three of four branches did not reopen any old result body; none reopened an
action payload. This is the desired separation between progress signal and
exact evidence.

## Remaining behavioral cautions

1. **Opaque bindings remain copy-fragile.** One seed transcribed the current
   candidate ID incorrectly despite it being resident. Exact host rejection is
   necessary. One occurrence does not earn a new aliasing feature.
2. **Access can induce confirmation.** One closure seed reopened an observation
   result and reread current source even though the compact frame already made
   closure mechanically clear. Exact access should remain available, but its
   presence is not automatically economical.
3. **The diagnostic task named the payload class.** The task required reopening
   the historical patch's old/new fields. This proves comprehensibility and
   exact access, not spontaneous discovery in an open large-world task.
4. **The evidence is development-only.** The donor paths were exposed, and the
   marker case was sacrificial. A fresh large-world comparison is still needed.

## Host defects

No host defect affected model behavior or terminal quality. The sole rejected
action was the intended stale-binding guard. The post-run seal-verifier write
bug affected only a repository copy during analysis and was fully restored from
the immutable external evidence; see `APPARATUS_FINDING.md`.
