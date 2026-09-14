"""Run the exact added examples against the qualified candidate's parser."""
import doctest
import sys
import types
from pathlib import Path

import study
from working_set_exp.jsonutil import sha256_file

AREA = Path(__file__).resolve().parent
FOLDER = AREA / "qualification-002"
data = study.read(FOLDER / "final-candidate.json")
files = {r["path"]: r["content_utf8"] for r in data["files"]}
patch = study.read(FOLDER / "steps/Q4-reply.json")["operation"]
addition = (study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8")
study.require(patch["new"] == addition + "\n" + patch["old"] and
              patch["new"] in files[patch["path"]], "not the actual added documentation")
parser = types.ModuleType("configparser")
parser.__file__ = "qualified-candidate/Lib/configparser.py"
saved = sys.modules.get("configparser")
try:
    sys.modules["configparser"] = parser
    exec(compile(files["Lib/configparser.py"], parser.__file__, "exec"), parser.__dict__)
    test = doctest.DocTestParser().get_doctest(addition, {}, "added_parser_examples", "REFERENCE_DOC.txt", 0)
    runner = doctest.DocTestRunner()
    result = runner.run(test)
finally:
    if saved is None:
        sys.modules.pop("configparser", None)
    else:
        sys.modules["configparser"] = saved
study.save(AREA, "DOCUMENTATION_CHECK.json", dict(status="passed" if result.failed == 0 else "failed",
    examples_attempted=result.attempted, failed=result.failed, model_completion_requests=0,
    candidate_json_sha256=sha256_file(FOLDER / "final-candidate.json"),
    actual_patch_sha256=sha256_file(FOLDER / "steps/Q4-reply.json"), script_sha256=sha256_file(Path(__file__)),
    classification="reviewer-authored documentation executed against isolated qualified source"))
study.require(result.failed == 0 and result.attempted > 0, "documentation examples fail")
print(result)
