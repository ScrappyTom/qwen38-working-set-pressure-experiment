# Saved work remains incomplete

The starting candidate is
`389292f683634a48a33bb8abcd9d70953b885802d432816ca9d75c1ad4ce8fa6`;
the final candidate is
`df3a3e87a91fad3eb5215c14496a3888cc044dc713570092a0355d1d26de12f4`.
Only Doc/library/urllib.parse.rst changes in this attempt. The library and inherited
test contribution remain byte-identical. All original documentation lines remain
in order, consistent with the actual preservation check.

Direct review of the inherited two test methods confirms the requested text/ASCII
bytes cases, Unicode-decimal text case, exact class/args/diagnostic assertions and
construction-versus-property-access distinction. This is preserved prior work, not
new live test authorship. The ordinary control and 72 targeted faults remain checked
by the unchanged public workflow.

The documentation adds focused port rules and executable examples. Its first edit
has four failures among fourteen examples. Its second edit corrects the three
exception-format failures through try/except output, without changing the library.
One example still expects an empty-port exception although actual execution returns
no output. The bullet asserting that an empty port raises is also false. A public
failure and inaccurate prose mean this contribution is not successful.

The opening prose should be read narrowly as port validation: malformed URL
structure has separate construction failures already documented immediately after
the insertion. A later independent review must check scope, prose and structure as
well as the example checker. A passing example subset alone cannot certify every
sentence or infer semantic truth from the current account.

No reviewer changed the artifact. saved-contribution.patch records the actual work;
the next continuation receives that work, its current real failed check, and the
authored account, including its errors.
