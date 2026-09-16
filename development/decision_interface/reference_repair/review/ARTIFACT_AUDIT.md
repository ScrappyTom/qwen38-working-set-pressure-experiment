# Saved work and unaccepted proposal

The continuation's starting and final candidates are byte-identical:
389292f683634a48a33bb8abcd9d70953b885802d432816ca9d75c1ad4ce8fa6.
Corrected tests remain saved and tests-checked. Those fourteen exact-class additions
came from the real C14 public reply applied during separately qualified replay,
not from a new edit in this continuation. Documentation remains unchanged.

C05 emits a public documentation proposal, preserved in its raw response and
EVT-0037. It is rejected before mutation because the anchor matches twice. Therefore
no examples/public check executes, and no test result establishes the proposal.
Do not silently choose an occurrence or relabel this as saved documentation.

Direct review of the proposed insertion finds self-contained urlsplit examples for
80, 0, 65535, absent/empty port and three invalid ASCII text ports. None-valued
interactive expressions correctly have no output. Error messages match the already
checked source/tests. The proposal makes an overbroad statement that both parsing
functions construct successfully and ValueError occurs only on port access: unrelated
invalid URL structure can fail at construction, as even the surrounding documentation
states. The explanation needs explicit port-specific scope. The explanatory prose
inside the doctest block is indented as block content rather than ordinary prose.
These are independent review limitations, not executed example failures.

The task does not explicitly demand a duplicate doctest for every regression target;
do not invent that additional acceptance condition because the proposal uses only
urlsplit text examples. It nevertheless remains unaccepted and untested work, with
no complete new contribution or submission.
