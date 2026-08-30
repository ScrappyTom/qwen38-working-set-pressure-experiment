import sys
sys.path.insert(0, "src")
from addressable_information_layer.content_log import ContentLog
from addressable_information_layer.artifact_units import build_address_map, import_artifact
from addressable_information_layer.summary_graph import build_summary_graph, summary_graph_status

log = ContentLog()
a = import_artifact(log, kind="python", path_or_name="a.py", text="def a():\n    return 1\n")
b = import_artifact(log, kind="python", path_or_name="b.py", text="def b():\n    return 2\n")
artifacts = {x.artifact_id: x for x in (a, b)}
maps = {x.artifact_id: build_address_map(x) for x in (a, b)}
summaries, graph = build_summary_graph(artifacts, maps)
status = summary_graph_status(summaries, graph, {a.artifact_id: maps[a.artifact_id]})
assert status["collection_stale"] is True
assert status["missing_artifact_ids"] == [b.artifact_id]
print("public passed")
