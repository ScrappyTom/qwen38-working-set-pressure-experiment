"""Preserve a real larger-source maintenance candidate and reproduce its fault.

Read-only upstream acquisition and offline candidate checks; no model calls.
The known historical backport is not a fresh investigation-capability benchmark.
"""
from pathlib import Path
import importlib.util
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp.candidate import Candidate, CandidateError
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

AREA = Path(__file__).resolve().parent
OUTPUT = AREA / "donor-001"
TAG = "v3.12.10"
PATHS = ("Lib/configparser.py", "Lib/test/test_configparser.py", "Doc/library/configparser.rst", "LICENSE")


def main():
    if OUTPUT.exists():
        raise FileExistsError("preserve the existing donor acquisition")
    OUTPUT.mkdir(parents=True)
    files, records = {}, []
    status = "incomplete"
    try:
        for name in PATHS:
            url = f"https://raw.githubusercontent.com/python/cpython/{TAG}/{name}"
            request = urllib.request.Request(url, headers={"User-Agent": "Qwen-working-set-task-preparation"})
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                receipt = dict(status=response.status, url=response.geturl(), etag=response.headers.get("ETag"))
            path = OUTPUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            raw.decode("utf-8")
            files[name] = raw
            records.append(dict(path=name, url=url, receipt=receipt, size_bytes=len(raw),
                sha256=sha256_file(path), lines=len(raw.splitlines()),
                maximum_line_bytes=max(map(len, raw.splitlines()), default=0)))
        module_path = OUTPUT / "Lib/configparser.py"
        spec = importlib.util.spec_from_file_location("screened_configparser", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = []
        for label, text in (
            ("bare_option", "[service]\noptional_flag\n"),
            ("ordinary_continuation", "[service]\nmessage = first\n    second\n"),
            ("bare_option_continuation", "[service]\noptional_flag\n    continuation\n"),
            ("bare_option_then_comment", "[service]\noptional_flag\n    # comment\nother = value\n"),
        ):
            parser = module.ConfigParser(allow_no_value=True)
            try:
                parser.read_string(text, source="customer.ini")
                actual = dict(status="parsed", values=dict(parser.items("service")))
            except Exception as error:
                actual = dict(status="raised", error_type=type(error).__name__, message=str(error))
            cases.append(dict(label=label, input=text, actual=actual))
        assert cases[2]["actual"]["error_type"] == "AttributeError"
        assert cases[0]["actual"]["values"] == {"optional_flag": None}
        assert cases[1]["actual"]["values"] == {"message": "first\nsecond"}
        assert cases[3]["actual"]["values"] == {"optional_flag": None, "other": "value"}
        default_rejected = []
        for name, raw in files.items():
            try:
                Candidate.create({name: raw})
            except CandidateError as error:
                default_rejected.append(dict(path=name, detail=str(error)))
        candidate = Candidate.create(files, max_file_bytes=1_048_576)
        result = dict(status="candidate_screened_not_prepared_for_inference", completion_requests=0,
            source_tag=TAG, records=records, baseline_cases=cases, default_rejected=default_rejected,
            candidate_id=candidate.candidate_id, selected_file_limit=candidate.max_file_bytes,
            total_source_bytes=sum(map(len, files.values())), source_files=len(files),
            upstream_tests_executed=False,
            limitations="Known historical maintenance task; no freshness or investigative-reversal claim. "
                        "Complete model input/feedback, task checks and continuation are not prepared yet.")
        (OUTPUT / "SCREEN.json").write_bytes(canonical_json_bytes(result))
        status = "candidate_screened_not_prepared_for_inference"
    except BaseException as error:
        (OUTPUT / "FAILED.json").write_bytes(canonical_json_bytes(dict(error_type=type(error).__name__, message=str(error))))
        raise
    finally:
        (OUTPUT / "SEAL.json").write_bytes(canonical_json_bytes(dict(status=status, completion_requests=0,
            script_sha256=sha256_file(Path(__file__)), files=[dict(path=p.relative_to(OUTPUT).as_posix(),
                size_bytes=p.stat().st_size, sha256=sha256_file(p)) for p in sorted(OUTPUT.rglob("*")) if p.is_file()])))
    print({"status":status, "bytes":result["total_source_bytes"], "files":len(files),
           "baseline_failure":cases[2]["actual"], "completion_requests":0})


if __name__ == "__main__":
    main()
