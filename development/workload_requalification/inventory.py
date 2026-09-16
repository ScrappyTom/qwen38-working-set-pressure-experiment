"""Inventory tracked task texts without counting copied checkouts as new tasks."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
AREA = Path(__file__).resolve().parent


def collect(root):
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    groups = {}
    for name in files:
        p = root / name
        if p.name.lower() not in ('task.txt','task.md','task.input') or not p.is_file():
            continue
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        row = groups.setdefault(digest, dict(task_sha256=digest, bytes=len(raw),
            first_line=raw.decode('utf-8-sig').splitlines()[0], locations=[],
            reconciliation='pending_entry_and_exposure_mapping'))
        row['locations'].append(name)
    return dict(repository=str(root), task_texts=list(groups.values()))


if __name__ == '__main__':
    result = dict(scope='Tracked task.txt/task.md/task.input inventories; generated/embedded tasks remain separately required.',
        repositories=[collect(ROOT), collect(ROOT.parent/'qwen38_metadata_working_set_docs_v0_2')],
        duplicate_worktrees=['qwen38-large-source-config', '.local/bounded-capacity-repair'])
    (AREA/'INVENTORY.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print([(Path(r['repository']).name, len(r['task_texts']),
            sum(len(t['locations']) for t in r['task_texts'])) for r in result['repositories']])
