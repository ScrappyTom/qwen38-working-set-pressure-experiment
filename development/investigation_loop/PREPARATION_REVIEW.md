# Two-run ordinary-loop preparation review

The concrete package is ready for the existing separate execution decision.
Preparation made **zero completion calls**. The proposed scope is L01 then L02,
seeds 104729 and 130363, at most 20 requests/actions each, **40 total**. Both
start independently from the same initial candidate with no history. Qwen
chooses its actions; no scripted sequence enters either initial input.

This qualifies the host path and a bounded development workload. It establishes
neither Qwen task success nor comfortable room for arbitrary exploration. The
focused correction path comes close to its input ceiling; broader exploration
can exceed it. Preserve that distinction when deciding and interpreting the pilot.

## Actual input and interface review

The package preserves the 25-file/128,524-byte stale-map fixture, TASK.txt and
PUBLIC_CHECK.py from the completed offline work. The check's genuine diagnostic
identifies a stale map. Retain that clue and limit discovery claims accordingly.
There is no new hidden grader; passing the public assertions is not universal
correctness or proof of donor identity. Final changes still require direct review.

The [initial native input](preparation-001/initial/L01-rendered-prompt.txt) was
directly read in full. It contains the task, current candidate/root orientation,
empty event/observation history, numerical allowance and complete tool reference.
The second initial native input is byte-identical; its endpoint seed differs.
Neither contains target paths, oracle actions, a known repair, prior results or
private thinking. The resource state contains no procedural correction example.
The retained navigation instruction describes scope and leaves discovery to Qwen.

The [reference](preparation-001/TOOL_REFERENCE.txt) still derives every required
argument form from the output schema. Source-reviewed effects now explain
immediate and historical-wrapper limits, validation before state changes,
historical source applicability, checker execution versus accepted return,
and normal outline-limit rejection. These facts were checked against the
repaired host. The underlying operations and guards are unchanged by this
preparation. No further naming comparison or metadata architecture was added.

All event payloads stay resident. Exact saved-result/event access remains
available with canonical originals; no externalization or automatic reacquisition
occurs. Private thinking is saved separately and omitted from later inputs.
The runner reconstructs each input from actual ordered action/result history
and checks every resident pair before dispatch. Rendering or saving an input
alone is not delivery to the model.

## Capacity and correction opportunity

Use Qwen3.8-27B UD-IQ3_XXS, q4_0 K/V at 56,576 context, no MTP, native thinking
on/xhigh/uncapped, and the pinned b10434 runtime/template. G=32,768 remains a
prospective generation reserve, so native input must be at most **23,808**.
This is reserve-based admission, not an output cap or observed physical exhaustion.

| Prepared path | Actions | Peak native input | Physical generation space at peak | Admission result |
|---|---:|---:|---:|---|
| Initial L01 / L02 | 0 | 3,070 | 53,506 | Both fit; identical native bytes |
| Direct oracle loop | 10 | 11,425 | 45,151 | Every input fits |
| Focused discovery/correction | 17 | 23,554 | 33,022 | Fits with only 254 tokens above G |
| Broader discovery/correction | 18 | 27,497 | 29,079 | First denial at input 15; later states are counterfactual |

The broader path additionally reads the record definitions. Its first denied
input is **23,827 tokens**, just 19 above the ceiling, before corrective rereading.
After its failed check at action 14, six actions remain, but the host could not
send the next input under this rule. Later oracle repair/check/submission cannot
be represented as an admitted live closure. The executed plain-message precheck
that exposed this limit is preserved in [ALLOWANCE_PRECHECK.json](ALLOWANCE_PRECHECK.json).

The focused path inspects reopening, patch application, address-map construction
and content logging, uses structure/search, makes an unsuccessful edit, consumes
the failed check, reads changed source, corrects it, checks the successor and
submits. Its checks occur at actions 11, 13 and 16; seven actions remain after
the unsuccessful edit's check, and subsequent inputs fit. It finishes with
three actions unused. This supports the proposed 20-action allowance without
inheriting the old 24-call limit. It does not guarantee that other useful
acquisitions or action orders will fit or finish.

Qwen may choose broader exploration. The actual guard will stop that path when
necessary. The host will not remove evidence, change the reserve or KV preset,
cap thinking, force submission, or manufacture a continuation. This is an
ordinary loop with a finite allowance, not a 25k pressure comparison.

Minimum free GPU memory was **563 MiB during rendering/tokenization**. The
runtime reported the expected context, q4, full offload and disabled MTP, without
truncation or CUDA failure. This does not qualify generation on the larger
inputs or replace earlier inference-memory evidence. Retain the accepted
advisory policy and monitoring; no renewed numeric-margin decision is needed.
Owned runtime/monitor shutdown and port release were recorded before sealing.

## Verification and execution readiness

[FOCUSED_TESTS.json](FOCUSED_TESTS.json) records **14 passing pilot-specific
checks**, with mocked endpoints and zero inference, exercising the actual
reused response handler. Coverage includes complete result feedback, successor
bindings, independent histories, omitted thinking, canonical payload custody,
source/manifest drift, capacity denial, 20-action exhaustion, ordinary rejection,
unchecked terminal submission, partial transport, incomplete output, incorrect
usage, required approval and refusal to reuse an existing attempt. This is not
a full-suite run.

[PREPARATION_TESTS.json](PREPARATION_TESTS.json) preserves the earlier combined
attempt: its 14 pilot tests passed, but setup of the historical comparison suite
failed because it requires the old source closure. The intentional return/
navigation repairs changed that source. No old freeze or test was rewritten to
make the setup pass; the dedicated pilot result is separate.

The [offline verifier](../../scripts/verify_investigation_preparation.py) checked
242 sealed public files, three local private-runtime files, 97 chained records,
and 51 prepared source/test/contract identities. It independently recounted
33 distinct native texts with the pinned CLI tokenizer, covering all 47 saved
inputs. It replayed 45 oracle actions against exact results and successors,
checking the resident history before each action. Replay uses the actual
executor, not an independent implementation of tool semantics. Mechanical
verification does not certify direct reading or model behavior.
[VERIFICATION.json](VERIFICATION.json) records the exact scope.

The runner validates the reviewed package hash, actor, schedule, source and
sealed artifacts; reconstructs both first API requests; and checks each first
native input against preparation. It saves input/before-state before dispatch,
preserves raw output before parsing, checks usage and runtime health, executes
at most one action, saves exact results/successors and newly created canonical
payloads, and records the next-turn decision separately.

Submission ends a run with its actual current-check flag. Legitimate tool
rejections and failed checks may receive another turn within the allowance.
Input denial or action exhaustion ends that run. Transport, protocol, runtime
or custody failure stops the attempt and withholds later runs. The one reserved
attempt is sealed after runtime closure, including partial evidence. The five
existing audit products are required after exposure, including successful paths.
No automatic successor follows.

## Frozen identities and execution decision

| Artifact | SHA-256 |
|---|---|
| Package manifest | `6c4ae13079c093c73b0b29ea7a830e66081e0344a0be088dc1dde3785b48ed93` |
| Preparation seal | `9197f9e3f366f9146c68dbbc0c42969edf3e292af298ddf4f6e911119ce8a080` |

The [specification](SPEC.md) defines exact scope and stop/review rules. The
existing [proposal](PROPOSAL.md) reserves a separate execution decision after
preparation. The current direction followed the recommendation to prepare this
package for that decision; no instruction to execute the newly frozen forty-call
maximum has been supplied. No completion request has been sent.

After approval, use local model/server paths from the supplied handoff; keep
those paths out of Git. The executable invocation is:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
py -3.12 -B -X utf8 scripts/run_investigation_loop.py --model $modelPath --server $serverPath --package-sha256 6c4ae13079c093c73b0b29ea7a830e66081e0344a0be088dc1dde3785b48ed93 --owner-approval '<actual owner instruction authorizing the two prepared runs>'
```
