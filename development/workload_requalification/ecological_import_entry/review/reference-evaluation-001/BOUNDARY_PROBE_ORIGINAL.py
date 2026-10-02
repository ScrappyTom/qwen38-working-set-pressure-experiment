"""Additional post-hoc contract probe; never replaces the frozen E020 grader."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")
from addressable_information_layer.importers import fixture_from_directory

rows = []
with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    for name, data in (("a.txt", b""), ("b.txt", b"x"), ("c.txt", b"12345"), ("d.txt", b"123456"), ("ignored.bin", b"")):
        (root / name).write_bytes(data)
    (root / ".git").mkdir()
    (root / ".git" / "excluded.txt").write_bytes(b"")
    # Independently stated expectations from the task's at-most-N and inclusive
    # byte-size contract. Do not ask a donor implementation for the answer.
    for byte_limit, eligible in ((0, ["a.txt"]), (1, ["a.txt", "b.txt"]), (5, ["a.txt", "b.txt", "c.txt"])):
        for file_limit in (0, 1, 2, 10):
            actual = fixture_from_directory(root, max_files=file_limit, max_file_bytes=byte_limit)["artifacts"]
            expected = [{"path": path} for path in eligible[:file_limit]]
            rows.append({
                "max_files": file_limit, "max_file_bytes": byte_limit,
                "expected": expected, "actual": actual, "passed": actual == expected,
            })
print(json.dumps(rows, separators=(",", ":")))
sys.exit(0 if all(row["passed"] for row in rows) else 1)
