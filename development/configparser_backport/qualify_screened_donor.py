"""Continue the offline donor screen with correct raw-value observations.

The original acquisition and failed probe stay unchanged. No network or model calls.
"""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp.candidate import Candidate, CandidateError
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

AREA = Path(__file__).resolve().parent
DONOR, OUTPUT = AREA / "donor-001", AREA / "screen-002"


def main():
    if OUTPUT.exists():
        raise FileExistsError("preserve the existing continuation")
    seal = load_json_strict((DONOR / "SEAL.json").read_bytes())
    assert seal["status"] == "incomplete"
    assert sha256_file(AREA / "screen_donor.py") == seal["script_sha256"]
    for row in seal["files"]:
        path = DONOR / row["path"]
        assert path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"]
    names = ("Lib/configparser.py", "Lib/test/test_configparser.py", "Doc/library/configparser.rst", "LICENSE")
    files = {name: (DONOR / name).read_bytes() for name in names}
    spec = importlib.util.spec_from_file_location("screened_configparser", DONOR / "Lib/configparser.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    OUTPUT.mkdir()
    status = "incomplete"
    try:
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
                actual = dict(status="parsed", raw_items=dict(parser.items("service", raw=True)),
                    interpolated_items=dict(parser.items("service")),
                    get_values={name: parser.get("service", name) for name in parser.options("service")})
            except Exception as error:
                actual = dict(status="raised", error_type=type(error).__name__, message=str(error))
            cases.append(dict(label=label, input=text, source="customer.ini",
                constructor=dict(allow_no_value=True), actual=actual))
        # Preserve observations even if a subsequent screen assertion is wrong.
        (OUTPUT / "baseline-cases.json").write_bytes(canonical_json_bytes(cases))
        assert cases[0]["actual"]["raw_items"] == {"optional_flag": None}
        assert cases[0]["actual"]["interpolated_items"] == {"optional_flag": ""}
        assert cases[0]["actual"]["get_values"] == {"optional_flag": None}
        assert cases[1]["actual"]["raw_items"] == {"message": "first\nsecond"}
        assert cases[2]["actual"]["error_type"] == "AttributeError"
        assert cases[3]["actual"]["raw_items"] == {"optional_flag": None, "other": "value"}
        rejected = []
        for name, raw in files.items():
            try:
                Candidate.create({name: raw})
            except CandidateError as error:
                rejected.append(dict(path=name, detail=str(error)))
        candidate = Candidate.create(files, max_file_bytes=1_048_576)
        result = dict(status="candidate_screened_not_prepared_for_inference", completion_requests=0,
            upstream_tag="v3.12.10", baseline_failure=cases[2]["actual"],
            candidate_id=candidate.candidate_id, selected_file_limit=candidate.max_file_bytes,
            default_rejected=rejected, source_files=len(files), total_bytes=sum(map(len, files.values())),
            donor_seal_sha256=sha256_file(DONOR / "SEAL.json"),
            records=[dict(path=name, url=f"https://raw.githubusercontent.com/python/cpython/v3.12.10/{name}",
                size_bytes=len(raw), sha256=sha256_file(DONOR / name), lines=len(raw.splitlines()),
                maximum_line_bytes=max(map(len,raw.splitlines()),default=0)) for name,raw in files.items()],
            upstream_tests_executed=False,
            initial_probe_error="items() with default interpolation exposes a bare value as an empty string; raw=True and get() retain None. The probe assumption was corrected, not donor code.",
            limitations="Known historical backport candidate, not a fresh discovery benchmark. Model input, feedback, full acceptance checks, and continuation are not yet qualified.")
        (OUTPUT / "SCREEN.json").write_bytes(canonical_json_bytes(result))
        status = result["status"]
    except BaseException as error:
        (OUTPUT / "FAILED.json").write_bytes(canonical_json_bytes(dict(error_type=type(error).__name__, message=str(error))))
        raise
    finally:
        (OUTPUT / "SEAL.json").write_bytes(canonical_json_bytes(dict(status=status, completion_requests=0,
            source_sha256={"script":sha256_file(Path(__file__)), "candidate":sha256_file(ROOT / "src/working_set_exp/candidate.py")},
            files=[dict(path=p.relative_to(OUTPUT).as_posix(), size_bytes=p.stat().st_size, sha256=sha256_file(p))
                   for p in sorted(OUTPUT.rglob("*")) if p.is_file()])))
    print({"status":status,"source_files":len(files),"total_bytes":result["total_bytes"],
           "default_rejections":len(rejected),"completion_requests":0})


if __name__ == "__main__":
    main()
