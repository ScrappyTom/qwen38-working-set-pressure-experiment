"""Execute examples touched by documentation changes, with their actual output."""
import difflib
import doctest
import io


def check_added_examples(before, after, filename):
    changed = [(j1, j2) for kind, i1, i2, j1, j2 in
               difflib.SequenceMatcher(None, before.splitlines(True), after.splitlines(True), autojunk=False).get_opcodes()
               if kind in ("insert", "replace")]
    try:
        parsed = doctest.DocTestParser().get_doctest(after, {}, "changed_documentation", filename, 0)
        selected = [e for e in parsed.examples if any(
            first < e.lineno + len(e.source.splitlines()) + len(e.want.splitlines()) and last > e.lineno
            for first, last in changed)]
        case = doctest.DocTest(selected, {}, parsed.name, filename, 0, after)
        output = io.StringIO()
        result = doctest.DocTestRunner().run(case, out=output.write)
        return dict(examples=result.attempted, failures=result.failed,
                    successful=result.attempted > 0 and result.failed == 0,
                    details=output.getvalue()[-2200:])
    except (ValueError, SyntaxError) as error:
        return dict(examples=0, failures=1, successful=False, details=str(error))
