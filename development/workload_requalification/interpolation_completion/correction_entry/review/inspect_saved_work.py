"""Preservation and ordinary examples on exact saved work; never edit the run."""
import ast
import contextlib
import difflib
import doctest
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import correction_task as entry
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes

task = entry.Task()
out = Path(__file__).parent/'run-001'
out.mkdir(exist_ok=True)
end = 'final' if (task.RUN/'final-candidate.json').exists() else 'stopped'
candidate = entry.original.candidate_from_snapshot(entry.original.read(task.RUN/f'{end}-candidate.json'))
before, after = task.inherited_candidate.file_map, candidate.file_map
changed = [p for p in before if before[p] != after[p]]
protected = {p: before[p] == after[p] for p in before if p not in (entry.TEST, entry.DOC)}

def nodes(raw):
    return {getattr(n, 'name', f'{type(n).__name__}:{i}'): ast.dump(n, include_attributes=False)
            for i,n in enumerate(ast.parse(raw.decode()).body)}

old_nodes, new_nodes = nodes(before[entry.TEST]), nodes(after[entry.TEST])
target = 'InterpolationMissingOptionErrorTransportTestCase'
unchanged_nodes = {name:new_nodes.get(name) == value for name,value in old_nodes.items() if name != target}
tree = ast.parse(after[entry.TEST].decode())
node = next((n for n in tree.body if getattr(n, 'name', None) == target), None)
if node is not None:
    (out/'saved_test_class.py').write_text(ast.get_source_segment(after[entry.TEST].decode(), node)+'\n', encoding='utf-8')

old_lines = before[entry.DOC].decode().splitlines(keepends=True)
new_lines = after[entry.DOC].decode().splitlines(keepends=True)
opcodes = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()
preserved_doc = all(tag in ('equal', 'insert') for tag,*_ in opcodes)
addition = ''.join(''.join(new_lines[b:e]) for tag,_,_,b,e in opcodes if tag != 'equal')
(out/'documentation_addition.rst').write_text(addition, encoding='utf-8')
(out/'saved_changes.diff').write_text(''.join(''.join(difflib.unified_diff(
    before[p].decode().splitlines(keepends=True), after[p].decode().splitlines(keepends=True),
    fromfile='before/'+p, tofile='after/'+p)) for p in changed), encoding='utf-8')

example_result = dict(examples=0, failures=0, output='', executed=False)
if addition.strip():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        library = folder/'configparser.py'
        library.write_bytes(after['Lib/configparser.py'])
        spec = importlib.util.spec_from_file_location('configparser', library)
        module = importlib.util.module_from_spec(spec)
        previous = sys.modules.get('configparser'); sys.modules['configparser'] = module
        try:
            spec.loader.exec_module(module)
            document = folder/'addition.rst'; document.write_text(addition, encoding='utf-8')
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                observed = doctest.testfile(str(document), module_relative=False, verbose=False)
            example_result = dict(examples=observed.attempted, failures=observed.failed,
                                  output=stream.getvalue(), executed=True)
        finally:
            if previous is None: sys.modules.pop('configparser', None)
            else: sys.modules['configparser'] = previous

result = dict(classification='Post-run reviewer preservation and ordinary example execution; no new model work',
    candidate_id=candidate.candidate_id, changed_files=changed, protected_files=protected,
    preserved_non_target_top_level_nodes=unchanged_nodes, original_document_lines_preserved=preserved_doc,
    examples=example_result, interpreter=sys.version, executable=sys.executable,
    exact_file_sha256={p:sha256_bytes(raw) for p,raw in after.items()})
(out/'ARTIFACT_REVIEW.json').write_bytes(canonical_json_bytes(result))
print(json.dumps({k:v for k,v in result.items() if k not in ('exact_file_sha256', 'preserved_non_target_top_level_nodes')}))
print('Protected test-file top-level nodes:', len(unchanged_nodes), 'all preserved:', all(unchanged_nodes.values()))
