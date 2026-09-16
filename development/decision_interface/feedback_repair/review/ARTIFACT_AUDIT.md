# Artifact audit

Review of the closed frozen run. Saved work and emitted-but-rejected proposals
are distinguished below; private drafts are not promoted into task artifacts.

## C13 saved contribution

Two methods are added inside the existing test class after
`test_urlsplit_attributes`. Each covers absence, empty port, zero, maximum port,
out-of-range, negative and noninteger ports for its API with text and ASCII bytes,
and a non-ASCII decimal digit with text. Construction occurs outside assertRaises,
so eager validation would fail these tests. Invalid cases assert complete args and
diagnostic text. The Unicode expected string uses Python's actual repr operation;
the private discussion's unsupported claims about repr are not saved constants.

The methods use assertRaises(ValueError), which accepts subclasses. They never
assert the exact class, despite the explicit task requirement. The saved ordinary
suite passes 74 tests, but the stronger tests-scope assessment fails all fourteen
independently targeted exception-class mutations. Its passing ordinary control and
complete required paths keep that result interpretable. The original 72 tests and
all documentation are preserved at this checkpoint.

The comments saying construction "always succeeds" are overbroad outside these
specific port cases: unrelated invalid URL structure can fail during construction.
The task requires the port-specific distinction. Any later documentation must keep
that scope. Passing these tests would not validate an unrestricted prose claim.

The patch is verbose and repeats assertions. That is not the substantive defect:
the missing exact-class protection is. No documentation contribution or checked
submission exists at this checkpoint.

## C14 public correction proposal, rejected by the host

The literal source reply reproduces the displayed 527-861 region with fourteen
`self.assertIs(type(ctx.exception), ValueError)` additions. The exact diff is saved
in rejected-proposal.diff. It also omits the final blank line and final separator.
The declared line-boundary rule would supply the separator before the unselected
following line; the omitted blank line is a separate cosmetic change. Every other
line is identical to the previously reviewed source.

This is an emitted public proposal, not a private draft. Its expected candidate and
region match the actual input. The host's resolver fails before applying it or
executing a check, so it is neither saved correction nor passing task evidence.
The proposal contains the missing exact-type checks and preserves the rest of the
test logic; a prospective repaired-host qualification must still execute it and its
real checker before claiming that it would pass. Documentation remains untouched.

C15 emits the identical operation. Both proposals remain rejected and the final
candidate is the C13 candidate, 675b65db319f94585f051bdab98895b34c3233a1d8022b2ffc09e2f7710df97d.
The saved patch adds only the two reviewed methods. Original test methods, library,
documentation and support files remain unchanged. The missing exact-class coverage
and missing documentation prevent a complete contribution. No new reviewer-written
patch was inserted into this attempt.
