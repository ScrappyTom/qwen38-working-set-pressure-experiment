"""Evaluator-only contribution; never added to a model task input."""
import completion_task as entry


def test_addition():
    source = (entry.original.legacy.AREA / 'REFERENCE_TEST.py').read_text(encoding='utf-8')
    source = source.replace("                expected_args = ('value', 'main', raw, reference)",
        """                expected_args = ('value', 'main', raw, reference)
                expected_message = (
                    "Bad value substitution: option 'value' in section 'main' contains "
                    f"an interpolation key {reference!r} which is not a valid option name. "
                    f"Raw value: {raw!r}")
                self.assertEqual(str(error), expected_message)""")
    return source


def doc_addition():
    import textwrap
    return ('Missing-reference lookups\n-------------------------\n\n' +
            textwrap.dedent((entry.original.legacy.AREA / 'REFERENCE_DOC.txt').read_text(encoding='utf-8')))


def candidate(test=None, doc=None, mutate=None):
    initial = entry.Task().inherited_candidate
    files = dict(initial.file_map)
    if test is not None: files[entry.TEST] += b'\n\n' + test.encode()
    if doc is not None: files[entry.DOC] += b'\n\n' + doc.encode()
    if mutate: mutate(files)
    return entry.Candidate.create(files, max_file_bytes=initial.max_file_bytes)
