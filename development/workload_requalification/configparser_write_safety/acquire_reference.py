"""Acquire pinned, evaluator-only CPython reference material; no model call."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

AREA = Path(__file__).resolve().parent
REVISION = 'ebf955df7a89ed0c7968f79faec1de49f61ed7cb'
PATHS = ('Lib/configparser.py', 'Lib/test/test_configparser.py',
         'Doc/library/configparser.rst', 'LICENSE')


def main():
    folder = AREA / 'upstream'
    folder.mkdir(exist_ok=True)
    assert not any(folder.iterdir()), 'Reference acquisition already contains files'
    rows = []
    for name in PATHS:
        url = f'https://raw.githubusercontent.com/python/cpython/{REVISION}/{name}'
        with urlopen(url, timeout=60) as response:
            raw = response.read()
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        rows.append(dict(path=name, url=url, size_bytes=len(raw),
                         sha256=hashlib.sha256(raw).hexdigest()))
    value = dict(repository='https://github.com/python/cpython', tag='v3.14.0',
                 tag_object='ac991beb29b1783316c4016c99468c008568d08a',
                 revision=REVISION, acquired_at=datetime.now(timezone.utc).isoformat(),
                 purpose='evaluator reference, excluded from actor candidate', files=rows)
    (folder / 'MANIFEST.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
