"""Execute the actual saved examples after closure, without correcting the artifact."""
import doctest
import io
import sys
import types

import recovery_task as task
from working_set_exp.jsonutil import sha256_file

folder = task.Task().RUN
task.study.require((folder / "RESPONSE_SEAL.json").exists(), "close the run first")
candidate_path = folder / "final-candidate.json"
data = task.study.read(candidate_path)
files = {r["path"]:r["content_utf8"] for r in data["files"]}
operation_path = folder / "calls/C08-operation-01.json"
operation = task.study.read(operation_path)
action = operation["action"]
task.study.require(operation["result"]["accepted"] and action["path"] == "Doc/library/configparser.rst"
                   and action["new"] in files[action["path"]], "not the actual accepted documentation")
parser = types.ModuleType("configparser")
parser.__file__ = "actual-saved-candidate/Lib/configparser.py"
saved = sys.modules.get("configparser")
failures = io.StringIO()
try:
    sys.modules["configparser"] = parser
    exec(compile(files["Lib/configparser.py"], parser.__file__, "exec"), parser.__dict__)
    case = doctest.DocTestParser().get_doctest(action["new"], {}, "actual_C08_examples", action["path"], 0)
    checked = doctest.DocTestRunner().run(case, out=failures.write)
    probe = parser.ConfigParser(interpolation=parser.ExtendedInterpolation())
    probe.add_section("a")
    probe.add_section("b")
    probe.set("a", "r", "${b:gone}")
    try:
        probe.get("a", "r")
    except parser.InterpolationMissingOptionError as error:
        observed = dict(arguments=list(error.args), attributes=vars(error),
                        rawval_attribute_exists=hasattr(error, "rawval"))
    else:
        raise AssertionError("the actual source did not raise the expected exception")
finally:
    if saved is None:
        sys.modules.pop("configparser", None)
    else:
        sys.modules["configparser"] = saved
result = dict(classification="post-closure execution of exact saved documentation; no corrections or actor feedback",
    model_requests=0, examples_attempted=checked.attempted, failures=checked.failed,
    failure_details=failures.getvalue(), cross_section_observation=observed,
    source_sha256={p.relative_to(task.study.ROOT).as_posix():sha256_file(p) for p in
                  (candidate_path, operation_path, task.AREA / "review/check_docs.py")})
task.study.save(task.AREA / "review", "DOCUMENTATION_CHECK.json", result)
print(result["failure_details"])
print({k:result[k] for k in ("examples_attempted", "failures", "cross_section_observation")})
