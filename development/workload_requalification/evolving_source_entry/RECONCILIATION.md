# Original E18 information contract and declared changes

The source fresh bank has130files/1,117,043bytes, candidate3dfa888955adab1021a75c47f1e1400887a8a16b4fb920c190f60fdbae9fe882.
All files are authenticated against FIXTURE.json; each of the four required
ledgers has226lines/19,065bytes. Other ledgers and120background modules remain.
Public and hidden programs have identical SHA256
ab8f5397bf92f6536c67e70343807d4ab7b8be75bc103587f7eccbfbd8ec93f7.
They check policy, primary, secondary and combined rendering; neither checks
whether all required source was delivered or when an operation occurred.

Direct review covers the complete original cell01 shared001 coding input; the
relevant task, binding, exact source, accepted edits and failed-check fields of
cell01 X25 decisions009–015; their selected complete thinking/final actions and
actual results; and cell02's complete dynamic-primary response. It does not claim
a new complete review of all87 old responses or a replay of the original seal.
The original APPARATUS_FINDING.md and DIRECT_TRANSCRIPT_AUDIT.md remain references,
not substitutes for the actual input/output inspected for this decision.

Both primary proposals dynamically call active_prefix(). At that point the old
policy and two-line primary are actually visible. Cell01 later changes policy,
explicitly reacquires it, saves secondary, then receives a real public failure
showing that primary should still return the old prefix. Its last response infers
snapshot semantics but only requests source; the18-call boundary leaves no repair.
This justifies clarifying the intended task behavior before another run. It does
not establish that externalization caused the semantic error. The original
ambiguous assignment and all original grades stay unchanged.

CLARIFICATION.txt preserves the existing behavioral expectation explicitly: primary
keeps the value observed before policy mutation even in a fresh process, secondary
uses the value after mutation. No old literal, replacement source, preferred group
or account is supplied. The new TASK.txt includes the unchanged original plus this
declared clarification. Original task SHA256:
73f6782b6e36f4901ec5e1d692439e82734123de1d3e5686d29d4c579bd4fb6c.
The manifest separately binds original, combined task and clarification.

The current host refreshes selected source after edits. That truthful refreshed
view does not perform the original requested policy reacquisition. The evaluator
records both facts and checks that an actor-requested read/group acquisition of
changed policy reaches a subsequent decision before secondary work. Required
ledger coverage likewise uses exact presented ranges, not EOF flags, accounts,
accepted construction or accumulated path names. No additional mutation gate
or mandatory all-ledgers-together selection is introduced.

The binding diagnostic is a separately earned mechanical correction from E17
run001 C03/C04. The accepted current source and rejected final differ by one file
fingerprint digit while their candidate agrees. Feedback now identifies each
failed comparison and makes no claim that either value was historically current.
Tests replay the actual proposal, preserve source and authority on rejection,
exercise a valid correction without reacquisition, and retain missing-source
rejection. This changes feedback, not guard strength, editing authority or task
truth. It is not an efficiency result.

New24requests/72operations, optional accounts, bounded decision input and medium
uncapped generation differ from old18 one-operation calls/512-token reasoning.
No old R50/X25 condition is reproduced. A current success would qualify this
clarified source task and its actual transitions, not a causal comparison among
task wording, feedback and runtime policies. E18-OBS-HARBOR remains separate.
