"""Materialize the verified coding artifact without altering the recorded run."""
import difflib
import hashlib
import json
from pathlib import Path

AREA = Path(__file__).resolve().parents[1]


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, f'Refusing to replace differing output: {path}'
    else:
        path.write_bytes(raw)


def main():
    proof = json.loads((AREA/'review/VERIFICATION-001.json').read_bytes())
    assert proof['status'] == 'replayed_exactly' and proof['submitted']
    snapshot_path = AREA/'run-001/final-candidate.json'
    snapshot = json.loads(snapshot_path.read_bytes())
    assert snapshot['candidate_id'] == proof['final_candidate_id']
    origin = json.loads((AREA.parent/'configparser_write_safety/run-002/starting-candidate.json').read_bytes())
    before = {row['path']: row['content_utf8'] for row in origin['files']}
    folder = (AREA/'review/001/saved-work').resolve()
    rows, patches = [], []
    for row in snapshot['files']:
        target = (folder/row['path']).resolve()
        assert target.is_relative_to(folder)
        raw = row['content_utf8'].encode('utf-8')
        save(target, raw)
        rows.append(dict(path=row['path'], bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        old = before.pop(row['path'])
        if old != row['content_utf8']:
            patches.extend(difflib.unified_diff(old.splitlines(True), row['content_utf8'].splitlines(True),
                          fromfile='original/'+row['path'], tofile='saved/'+row['path']))
    assert not before
    save(AREA/'review/001/COMPLETE-LINEAGE-PATCH.diff', ''.join(patches).encode('utf-8'))
    manifest = dict(candidate_id=snapshot['candidate_id'],
                    snapshot_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
                    export_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    exact_utf8_materialization=True, files=rows)
    save(AREA/'review/001/SAVED-WORK.json',
         (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(candidate_id=manifest['candidate_id'], files=len(rows), output=str(folder))))


if __name__ == '__main__':
    main()
