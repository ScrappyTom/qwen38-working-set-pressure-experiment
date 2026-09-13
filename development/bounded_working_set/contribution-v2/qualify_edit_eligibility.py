"""Native offline admission of the diagnostic C07 fragment edit; no inference."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import bounded_parser as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count


area = Path(__file__).resolve().parent
run = area / "run-001"
output = area / "native-edit-002"
assert not output.exists(), "preserve the existing qualification"
task.base.verify_seal(run)
manifest = task.read(run / "EXECUTION_MANIFEST.json")
task.verify_sources(manifest["source_sha256"])
_, model, tokenizer = task.runtime_paths()
assert sha256_file(model) == task.ACTOR["model_sha256"]
assert sha256_file(tokenizer) == task.delivery.TOKENIZER_SHA
snapshot = task.read(run / "after/C06-state.json")
request = task.read(run / "admission/I0056-endpoint-request.json")
view = json.loads(request["messages"][1]["content"])
session = task.initial_session()
assert session.candidate.candidate_id == snapshot["candidate_id"]
for key, value in snapshot.items():
    if key != "candidate_id":
        setattr(session, key, copy.deepcopy(value))
assert task.request_for(session.view()) == request
session.mark_delivered(view)
output.mkdir()
trials = []


def measure(state):
    req = task.request_for(state)
    native = task.expected_native(req)
    count = tokenizer_count(SimpleNamespace(model_path=model, tokenizer_path=tokenizer), native)
    stem = f"I{len(trials)+1:04d}"
    task.save(output, stem + "-request.json", req)
    task.save(output, stem + "-native.txt", native)
    trials.append(dict(stem=stem, prompt_tokens=count,
                       request_sha256=sha256_bytes(canonical_json_bytes(req)),
                       native_sha256=sha256_bytes(native)))
    return count


assert measure(view) == 23281
assert (output / "I0001-native.txt").read_bytes() == (run / "admission/I0056-native.txt").read_bytes()
action = task.read(area / "EDIT_ELIGIBILITY_PROBE.json")["supplied_action"]
before = session.candidate
result = session.execute(action, measure)
assert result["accepted"] and not session.delivery_blocked
after_input = measure(session.view())
assert after_input <= 23808
assert session.view()["latest_feedback"]["result"] == result
assert before.file_map["Lib/configparser.py"] == session.candidate.file_map["Lib/configparser.py"]
assert before.file_map["Doc/library/configparser.rst"] == session.candidate.file_map["Doc/library/configparser.rst"]
assert session.candidate.file_map[action["path"]].decode() == before.file_map[action["path"]].decode().replace(action["old"], action["new"], 1)
task.save(output, "RESULT.json", dict(
    qualification="Restored C07 fragment edit through actual host and offline native tokenizer admission.",
    scope="Reviewer-supplied blank-line diagnostic only; no regression, model contribution or next-model receipt.",
    model_requests=0, server_requests=0, trials=trials, result=result,
    before_input_tokens=23281, after_input_tokens=after_input,
    remaining_input_tokens=23808-after_input,
    source_sha256=manifest["source_sha256"], script_sha256=sha256_file(Path(__file__)),
    model_sha256=task.ACTOR["model_sha256"], tokenizer_sha256=task.delivery.TOKENIZER_SHA,
    source_response_seal_sha256=sha256_file(run / "RESPONSE_SEAL.json"),
    final_candidate_id=session.candidate.candidate_id,
    repository_candidate_files_modified=False,
))
print("Native fragment edit accepted:", after_input, "input tokens; zero completions")
