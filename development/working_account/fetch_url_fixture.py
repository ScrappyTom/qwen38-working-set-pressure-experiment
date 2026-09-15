"""Acquire a version-pinned upstream maintenance world; no model inference."""
import hashlib
import json
from pathlib import Path
import urllib.request

AREA = Path(__file__).resolve().parent / "url_ports"
PATHS = ("Lib/urllib/__init__.py", "Lib/urllib/parse.py", "Lib/test/__init__.py",
         "Lib/test/test_urlparse.py", "Lib/test/support/__init__.py",
         "Lib/test/support/import_helper.py", "Lib/test/support/os_helper.py",
         "Lib/test/support/warnings_helper.py", "Doc/library/urllib.parse.rst", "LICENSE")


def obtain(url):
    request = urllib.request.Request(url, headers={"User-Agent": "working-set-experiment-source-preparation"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


if __name__ == "__main__":
    AREA.mkdir(exist_ok=False)
    # Resolve the annotated release tag before fetching each exact source version.
    ref = json.loads(obtain("https://api.github.com/repos/python/cpython/git/ref/tags/v3.12.0"))
    obj = ref["object"]
    if obj["type"] == "tag":
        obj = json.loads(obtain(obj["url"]))["object"]
    assert obj["type"] == "commit"
    rows = []
    for name in PATHS:
        url = f"https://raw.githubusercontent.com/python/cpython/{obj['sha']}/{name}"
        raw = obtain(url)
        path = AREA / "world" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        rows.append(dict(path=name, url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    (AREA / "SOURCE.json").write_text(json.dumps(dict(tag="v3.12.0", commit=obj["sha"], files=rows), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(commit=obj["sha"], files=len(rows), bytes=sum(r["bytes"] for r in rows))))
