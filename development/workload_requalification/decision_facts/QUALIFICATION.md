# Decision-facts qualification

The opt-in renderer projects phase coverage from previously delivered exact
current-file extents plus exact source in the proposed input. It does not commit
delivery, grant editing authority, infer understanding or rewrite an account.
Recent accepted region edits include their recorded result path even when the
original region has become stale. Frozen historical renderers remain unchanged.

Eight CPU checks pass in CPU-TESTS-003.log. They exercise actual pre-C14 ORBIT
state, pure/idempotent rendering and delivery, disjoint/overlapping extents,
changed/unchanged file versions, complete versus partial historical source,
recovery omissions, account text, phase release/current edit authority and
recorded edit targets/rejections. The first attempt shadowed unittest.run with
a fixture path. The second incorrectly encoded an account update as a public
operation instead of the supported top-level account field. Both logs remain;
these were qualification harness defects, not production-host changes.

Native002 measures complete old/new requests with the pinned runtime/template
and tokenizer, without model completions:

| Actual ORBIT checkpoint | Historical tokens | Projected tokens | Result |
| --- | ---: | ---: | --- |
| After C03 acquisition, before C04 | 23,794 | 23,835 | Projected counterfactual exceeds23,808; must not be sent unchanged |
| After C04 capacity rejection | 6,559 | 6,599 | Recovery remains usable; omitted selected source is not credited |
| After C13 tails, before C14 | 14,751 | 14,797 | Both records correctly display complete through this input |
| After C20 tails, before C21 | 15,672 | 15,712 | Both records correctly display complete through this input |

From the actual C04 rejection state, the saved public C05 replacement choice
executes successfully under the new view, leaves the candidate unchanged and
produces a12,200-token normal input. This is an offline replay of an already
recorded choice, not a new model result or a prediction that the actor would
choose it in another run.

The extra40–46tokens are a real presentation cost. The crowded historical state
cannot be imported into a live run without admission under the revised renderer.
The prospective COMPASS package starts empty and sizes every construction using
this view; its broad-acquisition/recovery qualification must confirm that path.
There is no policy exemption or input-limit increase.

Native001 is preserved too. Its C03/C20 selections accidentally used the account
operation's intermediate snapshot rather than the following acquisition. Those
measurements are truthful for those snapshots but do not qualify the intended
completed inputs. native-001-source/qualify_native.py preserves the exact first
script; native002 corrects only those two checkpoint names. The C14/recovery
measurements and saved-choice replay were already correct. No completion was sent
in either qualification; both owned runtimes closed.

This establishes mechanical projection and measured feasibility, not reduced
deliberation or improved account use. No unchanged ORBIT rerun is authorized by
this result. The next exposure is the separately declared original COMPASS task.
