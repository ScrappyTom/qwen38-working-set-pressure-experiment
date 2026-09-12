"""Independent offline assessment from sealed captures and saved files.

No completion requests or candidate edits. The diagnostic brace insertion below
is explicitly separate from the malformed artifact actually produced by C01.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "development/saved_work_continuation/run-001"
OUTPUT = Path(__file__).with_name("ARTIFACT_ASSESSMENT.json")


def read(path):
    return json.loads(path.read_bytes())


def decode_dump(text):
    """Accept AST constructor data, never evaluate arbitrary Python code."""
    def decode(node):
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name) and not node.args
            cls = getattr(ast, node.func.id)
            assert isinstance(cls, type) and issubclass(cls, ast.AST)
            assert all(k.arg in cls._fields for k in node.keywords)
            assert len({k.arg for k in node.keywords}) == len(node.keywords)
            return cls(**{k.arg: decode(k.value) for k in node.keywords})
        if isinstance(node, ast.List):
            return [decode(x) for x in node.elts]
        return ast.literal_eval(node)
    result = decode(ast.parse(text, mode="eval").body)
    assert isinstance(result, ast.Module)
    return result


def first_changed_expression(before, after):
    if isinstance(before, ast.AST) and isinstance(after, ast.AST):
        if type(before) is not type(after):
            assert isinstance(before, ast.expr) and isinstance(after, ast.expr)
            return ast.unparse(before), ast.unparse(after)
        for name in before._fields:
            found = first_changed_expression(getattr(before, name), getattr(after, name))
            if found:
                return found
    elif isinstance(before, list) and isinstance(after, list):
        assert len(before) == len(after)
        for a, b in zip(before, after):
            found = first_changed_expression(a, b)
            if found:
                return found
    return None


def files(tag):
    return {x["path"]: x["content_utf8"] for x in
            read(RUN / "calls" / (tag + "-candidate-after.json"))["files"]}


def main():
    assert not OUTPUT.exists(), "preserve the existing assessment"
    seal_sha = hashlib.sha256((RUN / "RESPONSE_SEAL.json").read_bytes()).hexdigest()
    assert seal_sha == "99055e218584b886244f7312a2fb6dde75859b1029c00331a613721b3cb827fe"
    pairs = read(RUN / "after/P2-03-C05-snapshot.json")["pairs"]
    captures = {}
    for pair in pairs:
        if pair["response"]["action"] == "reopen_observation":
            handle = pair["response"]["handle"]
            original = pair["result"]["exact_result_utf8"].encode()
            assert hashlib.sha256(original).hexdigest() == pair["result"]["exact_result_sha256"]
            captures[handle] = json.loads(original)
    original = decode_dump(captures["OBS-0001"]["ast_dump"])
    expected, views = [], {}
    for handle in ("OBS-0002", "OBS-0003"):
        emitted = decode_dump(captures[handle]["ast_dump"])
        before = [n for n in original.body if isinstance(n, ast.FunctionDef)]
        after = [n for n in emitted.body if isinstance(n, ast.FunctionDef)]
        assert [n.name for n in before] == [n.name for n in after]
        changed = [a.name for a, b in zip(before, after) if ast.dump(a) != ast.dump(b)]
        name, first = next((a.name, first_changed_expression(a, b)) for a, b in zip(before, after)
                           if first_changed_expression(a, b))
        expected.append(dict(capture=handle, changed_functions=changed,
            first_change=dict(function=name, before=first[0], after=first[1])))
        weibull = next(n for n in emitted.body if isinstance(n, ast.FunctionDef) and n.name == "weibullvariate")
        views[handle] = dict(compile_request=captures[handle]["compile_request"],
            weibull_return=ast.unparse(weibull.body[-1]),
            exact_weibull_return_dump=ast.dump(weibull.body[-1]))
    first_files, final_files = files("P1-01-C01"), files("P2-07-C09")
    first_text, final_text = first_files["reports/incident.json"], final_files["reports/incident.json"]
    try:
        json.loads(first_text)
    except json.JSONDecodeError as error:
        first_error = str(error)
    else:
        raise AssertionError("C01 is unexpectedly valid JSON")
    diagnostic = json.loads(first_text.rstrip("\n") + "}\n")
    assert diagnostic == {"builds": [expected[0]]}
    assert json.loads(final_text) == {"builds": expected}
    assert files("P2-03-C05") == final_files
    start = {x["path"]: x["content_utf8"] for x in read(RUN / "starting-candidate.json")["files"]}
    assert all(final_files[k] == v for k, v in start.items() if k != "reports/incident.json")
    request = read(RUN / "admission/P2-07-C09-x014-endpoint-request.json")
    frame = json.loads(request["messages"][1]["content"])
    event = frame["active_phase_event_frame"]["events"][14]
    shown = json.loads(event["result_body"]["fields"]["exact_result_utf8"])
    assert shown == captures["OBS-0002"]
    result = dict(status="independent_saved_artifact_assessment_passed", completion_requests=0,
        source_seal_sha256=seal_sha, assessment_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        expected_report_derived_from_captured_ast={"builds": expected}, capture_views=views,
        c01_actual_json_valid=False, c01_actual_error=first_error,
        c01_first_entry_matches_captured_facts_after_diagnostic_brace_insertion=True,
        diagnostic_brace_insertion_not_applied_to_saved_artifact=True,
        c01_report_bytes=len(first_text.encode()), final_report_bytes=len(final_text.encode()),
        final_report_matches_captures=True, first_entry_facts_preserved=True,
        c05_artifact_unchanged_through_submission=True, all_nonreport_files_unchanged_from_saved_repair=True,
        c09_resident_build_a_matches_saved_capture=True,
        c09_build_a_weibull_unary_minus_is_present=True,
        limitation="Artifact assessment and exact input facts, not a causal explanation of Qwen's thinking or new model performance evidence.")
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
