import sys
sys.path.insert(0, "src")
from addressable_information_layer.artifact_units import build_address_map, import_artifact
from addressable_information_layer.content_log import ContentLog
from addressable_information_layer.reopen import materialize_reopen

log = ContentLog()
artifact = import_artifact(log, kind="python", path_or_name="sample.py", text="def alpha():\n    value = 3\n    return value\n")
amap = build_address_map(artifact)
unit = amap.units["function:alpha"]
expected = "def alpha():\n    value = 3\n    return value"
receipt = materialize_reopen(unit.exact_ref, artifacts={artifact.artifact_id: artifact}, address_maps={artifact.artifact_id: amap}, max_chars=len(expected))
assert receipt.materialized_text == expected
assert receipt.truncated is False
short = materialize_reopen(unit.exact_ref, artifacts={artifact.artifact_id: artifact}, address_maps={artifact.artifact_id: amap}, max_chars=len(expected) - 1)
assert short.truncated is True and short.materialized_text == expected[:-1]
print("public passed")

artifact2 = import_artifact(log, kind="python", path_or_name="one.py", text="def one(): return 1\n")
amap2 = build_address_map(artifact2)
unit2 = amap2.units["function:one"]
r2 = materialize_reopen(unit2.unit_id, artifacts={artifact2.artifact_id: artifact2}, address_maps={artifact2.artifact_id: amap2}, max_chars=100)
assert r2.materialized_text == "def one(): return 1" and r2.truncated is False
print("hidden passed")
