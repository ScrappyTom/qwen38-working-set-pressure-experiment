import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, "src")
from addressable_information_layer.importers import fixture_from_directory
from addressable_information_layer.saved_runs import _embedded_artifacts_from_jsonl, _events_from_jsonl

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "a.txt").write_text("abcde", encoding="utf-8")
    (root / "b.txt").write_text("vwxyz", encoding="utf-8")
    lines = [json.dumps({"record_type": "receipts", "payload": {"index": i}}) for i in range(1, 1000)]
    lines.append(json.dumps({"record_type": "artifacts", "payload": {"artifact_ref": "edge", "artifact_kind": "text", "content": "line-1000"}}))
    (root / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    imported = fixture_from_directory(root, max_files=1, max_file_bytes=5)
    assert imported["artifacts"] == [{"path": "a.txt"}]
    assert len(_events_from_jsonl(root, "generic")) == 1000
    embedded = _embedded_artifacts_from_jsonl(root)
    assert len(embedded) == 1 and embedded[0]["text"] == "line-1000"
print("public passed")
