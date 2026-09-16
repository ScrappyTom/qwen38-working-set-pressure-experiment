# Saved artifact and public proposal review

Final candidate: `8b5860183d02645b5cd0667755c85cfe032e041ba033b2326a61cc3e8640ac9b`.
The [exact diff](saved-contribution.patch) changes only the requested test and
documentation files. The implementation, package files, license and every original
test method remain unchanged. No reviewer repair is applied.

## Tests: useful coverage with a material omission

The added `test_port_boundary_and_error_details` exercises urlsplit and urlparse,
text and ASCII bytes, absent/empty ports, 0/65535, and invalid 65536/negative/noninteger
ports, plus a Unicode decimal digit for text. Construction occurs before the
exception-catching block, so premature validation is observable. It checks concrete
accepted values and complete error argument tuples and messages.

Only the text invalid-port loop asserts `type(exception) is ValueError`. The bytes
loop uses `assertRaises(ValueError)`, which permits subclasses. Its docstring's claim
of exact-class coverage is therefore too broad. Redundant empty-port calls and a
weak netloc inequality add clutter; they do not repair the missing assertion. The
comment calling U+0966 Devanagari six is wrong (it is zero), while the actual test
still exercises a valid non-ASCII decimal-digit case.

The actual frozen tests scope passes after C08. The independent
[probe](artifact-probe-001/RESULTS.json) reconstructs all six final files from their
recorded bytes and verifies their hashes. Fresh CPU subprocesses run all 73 tests:

| Implementation used by the reviewer | Result |
| --- | --- |
| Unchanged saved parser | 73 pass |
| Only bytes port errors changed to a ValueError subclass | 73 pass |
| Only text port errors changed to that subclass | 1 failure |
| All port errors changed to that subclass | 1 failure |

The fault preserves arguments and messages, changing only exact exception class.
This demonstrates an evaluator false negative for the missing byte-input requirement.
It is not a new experimental score, model run, or alteration of the saved parser.

## Documentation: examples pass, preservation fails

C16 finally saves a literal source replacement. Its added explanation describes
the boundary values, absent/empty behavior, delayed port access, text/bytes errors
and rejection of non-ASCII digits. The 19 new executable examples pass in CHK-0038.
The None cases correctly expect no interactive output; the uncertain Unicode-output
example is omitted, with the behavior instead described in prose. The statement
that parsing succeeds "in every case" is explicitly about these shown examples.
It should not be generalized to malformed brackets or NFKC-invalid netlocs; separate
review probes confirm those can fail during construction.

Two differences cause the frozen preservation criterion to fail:

1. The port paragraph is expanded by replacing existing wording, rather than only
   inserting new lines. The information and reference remain, but the check requires
   original lines to be unchanged. The actual task says "Preserve existing
   documentation" without spelling out that exact insertions-only interpretation.
2. The replacement source ends without LF. Original line 237 ends with LF and is
   followed by more document text. The host concatenates the emitted bytes with the
   untouched tail, joining original lines 237 and 238. This changes line layout in
   unrelated query-parsing documentation. It does not delete the rest of the file
   or establish a new semantic error in that paragraph, but it is an unintended
   boundary effect and violates the exact preservation criterion.

The account/final calls the selected region the "full file." The host correctly
limits the operation to the referenced lines 1-237, retaining the unseen tail.
Transport preserves the 13,687 emitted source bytes exactly. The missing LF is in
the endpoint final itself, not removed by the decoder. Reliable whole-line editing
therefore needs a separate boundary contract; raw byte custody alone does not
prevent this effect. Neither silent normalization nor retroactive rejection is
applied to the historical result.

CHK-0038 reports tests and examples passing, documentation preservation failing,
and public failing. There is no submission and no subsequent actor input containing
that feedback. Do not label it an ignored failure or a completed correct contribution.

## Earlier rejected documentation remains distinct

The independently executed public fragments from C13, C14 and C15 are not applied
to a guessed occurrence. Their old text has two exact matches at lines 133 and 319;
C14 and C15 use the identical old fragment. Only the first occurrence is visible.

C13's nine examples pass. C14 has one failure among twelve examples: its input is
Devanagari zero but its expected message contains six. C15 has two failures among
seventeen examples because it expects literal `None` from bare expressions.
Its escaped Unicode spelling passes doctest comparison: Python 3.12's OutputChecker
folds both actual printable Unicode and expected hex escapes to ASCII. That is an
accepted comparison form, not evidence that the terminal prints the escape literally.

The final saved examples differ from these proposals and are assessed separately.
Fixing the match diagnostic would not, by itself, prove all proposed documentation
correct or establish a specific time saving.
