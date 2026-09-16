# Independent direct artifact review

The final candidate is
`6c8457e58581b4d1f5be475eece0ff80d3e52f3564b88392db8784463475e58c`.
This continuation changes only Doc/library/urllib.parse.rst: its empty-port bullet
now explains the None return, and the incorrect exception example becomes ordinary
`.port` access with no displayed result. These changes match the inspected text and
bytes `_hostinfo` normalization and the port property. No implementation changes or
test weakening occurs. The previous erroneous state remains archived.

Direct review of the complete inserted documentation confirms the boundary values,
negative and noninteger diagnostics, non-ASCII-decimal restriction, and the
construction-versus-port-access distinction. The opening statement concerns port
validation; the existing adjacent text continues to describe structural parse
failures. The examples import their API, preserve state in order, and use real
outputs. A None expression correctly produces no interactive output. The narrative
is focused on port behavior, not a claim of universal URL validation.

Both inherited test methods were read directly again. They cover urlsplit and
urlparse for text and ASCII bytes: missing/empty port, 0, 65535, 65536, negative and
noninteger values, plus Unicode-decimal text. Each error path asserts exact class,
complete arguments and diagnostic text. Construction precedes the assertion on
property access. The checks exercise the saved tests and all declared fault targets;
they are not replaced by a test of this reviewer's preferred implementation.

The recorded CHK-0061 independently runs the original 72-test suite, the 74-test
edited suite, required-path observation and all 72 targeted faults. All ordinary
tests and fourteen added examples pass; every target is detected against a passing
control. Existing-work and documentation-preservation checks pass. This review did
not rerun inference or the checker; it examined their complete preserved observation
and the actual artifact. Preservation is also confirmed by the saved file identities.

The contribution meets this task's requested tests/documentation contract. Tests
were produced and qualified earlier, and much of the documentation was inherited;
only the remaining correction is new live work here. This is a completed development
contribution, not a newly autonomous end-to-end backport or a general reliability
qualification.
