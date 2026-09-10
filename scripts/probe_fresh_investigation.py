"""Check a proposed investigation's failure geometry without exposing a model."""
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import admitted_donor_candidate
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank"
MAINTENANCE = ROOT / "maintenance/resume_after_020"
PROBE = MAINTENANCE / "fresh_investigation_probe.py"


def main():
    donor = admitted_donor_candidate(BANK)
    path = "src/addressable_information_layer/patching.py"
    before = b"    new_map = build_address_map(new_artifact)\n"
    after = b"    new_map = address_map\n"
    assert donor.file_map[path].count(before) == 1
    files = donor.file_map
    files[path] = files[path].replace(before, after)
    injected = Candidate.create(files)
    results = {}
    for name, candidate in (("unchanged_donor", donor), ("proposed_injected_fault", injected)):
        result = run_checker(candidate, PROBE.read_bytes())
        if not result["passed"] or result["streams_truncated"]:
            raise RuntimeError(result)
        results[name] = {"candidate_id": candidate.candidate_id, "observation": load_json_strict(result["stdout"].encode("utf-8"))}
    good = results["unchanged_donor"]["observation"]
    bad = results["proposed_injected_fault"]["observation"]
    assert good["current_reopen"]["status"] == "materialized"
    assert good["current_reopen"]["text"] == "def calculate():\n    interim = 2\n    return interim"
    assert good["old_exact_reference"]["status"] == "blocked"
    assert good["second_reopen"]["text"] == "def calculate():\n    return 3"
    assert good["unchanged_function_reopen"]["text"] == "def untouched():\n    return 7"
    assert bad["independent_extraction_correct"] and bad["current_reopen"]["status"] == "blocked"
    assert not bad["propagated_map_matches_updated_version"]
    output = {"scope": "offline task geometry only; no model exposure; not a frozen task bank",
              "probe_sha256": sha256_file(PROBE), "script_sha256": sha256_file(Path(__file__)),
              "bank_manifest_sha256": sha256_file(BANK / "BANK_MANIFEST.json"),
              "injection": {"path": path, "old": before.decode(), "new": after.decode()}, "results": results,
              "natural_pressure_qualified": False,
              "reason": "A correct short investigation may finish before pressure; source volume alone cannot establish a meaningful boundary."}
    target = MAINTENANCE / "INVESTIGATION_GEOMETRY.json"
    with target.open("xb") as stream:
        stream.write(canonical_json_bytes(output))
    print("Fresh fault geometry reproduced; current/stale/second-update contract distinguished. Natural pressure remains unqualified.")


if __name__ == "__main__":
    main()
