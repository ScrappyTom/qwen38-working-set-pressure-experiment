"""Acquire the pinned upstream dependencies used by test_configparser; no model calls."""
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

AREA = Path(__file__).resolve().parent
OUTPUT = AREA / "test-support-001"
PATHS = ("Lib/test/__init__.py", "Lib/test/support/__init__.py", "Lib/test/support/os_helper.py",
         "Lib/test/configdata/cfgparser.1", "Lib/test/configdata/cfgparser.2", "Lib/test/configdata/cfgparser.3")


def main():
    if OUTPUT.exists():
        raise FileExistsError("preserve existing acquisition")
    OUTPUT.mkdir()
    status, rows = "incomplete", []
    try:
        for name in PATHS:
            url = f"https://raw.githubusercontent.com/python/cpython/v3.12.10/{name}"
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read()
                receipt = dict(status=response.status, url=response.geturl(), etag=response.headers.get("ETag"))
            path = OUTPUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            rows.append(dict(path=name, size_bytes=len(raw), sha256=sha256_file(path), receipt=receipt))
        status = "acquired_not_yet_executed"
    except BaseException as error:
        (OUTPUT / "FAILED.json").write_bytes(canonical_json_bytes(dict(error_type=type(error).__name__, message=str(error))))
        raise
    finally:
        (OUTPUT / "SEAL.json").write_bytes(canonical_json_bytes(dict(status=status, completion_requests=0,
            script_sha256=sha256_file(Path(__file__)), files=rows)))
    print({"status":status,"files":len(rows),"bytes":sum(row["size_bytes"] for row in rows)})


if __name__ == "__main__":
    main()
