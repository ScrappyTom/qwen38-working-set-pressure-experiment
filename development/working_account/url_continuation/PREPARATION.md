# Qualified recovery package

105 selected host tests pass. Native qualification uses the same model runtime for
template rendering and tokenization only; it sends zero model completion requests.

| Qualification | Scripted requests | New operations | Native inputs | Custody records | Result |
|---|---:|---:|---:|---:|---|
| Complete contribution | 5 | 12 | 11 | 156 | Checked submission; exact replay |
| Failed test and correction | 6 | 15 | 14 | 193 | Failed tests, correction, public pass, submission; exact replay |
| Rejected account/group requests and recovery | 7 | 14 | 21 | 246 | Both rejections delivered, previous state retained, subsequent checked submission; exact replay |

All three start at 23,781 tokens with the actual broad source group, empty account
and corrected rejection. They bind 295 source files. The complete route's first
account plus replacement reduces its next input to 5,328 tokens; those choices and
account text are researcher-authored qualification, excluded from the live input.

The rejection route first requests a nonexistent source, then proposes an explicit
size-stress account too large even with an empty selection. Both produce complete
rejection feedback; neither changes the previous account or group. Its third input
is 23,805 tokens, and the subsequent joint account/group transition succeeds. The
48,941-token maximum *sizing trial* is rejected; it is not a dispatched model input
or task material. This is a useful near-limit control-path qualification, not a
guarantee for arbitrary account lengths, error text or future work.

The setup independently preserves and reexecutes the original C04 proposal. Its
15 native inputs and 108 custody records verify against 293 preparation sources.
SETUP.json contains the resulting rejection and unchanged candidate/group, with
new request/operation accounting. The existing task and system instruction are
unchanged; the updated operating reference describes joint admission. No prior
thinking, reference work or researcher-selected group is installed.

EXECUTION_MANIFEST.json freezes the exact first wire/native input, actor settings,
source identities, starting candidate, preparation and correction seals. The run
is one additional uncoached development continuation, bounded by 20 requests and
60 operations. All runtime owners closed after qualification; the accepted advisory
GPU-margin policy is unchanged. The original attempt and every offline result remain
separately sealed. No model outcome is claimed by this preparation.
