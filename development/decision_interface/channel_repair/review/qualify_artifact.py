"""Independent, post-closure artifact probes; never supplies feedback to Qwen.

Fresh subprocesses run the saved suite against the unchanged candidate parser and
input-family-specific exception-class faults. This is reviewer execution, not an
extra actor check, experimental score, or repair of the submitted artifact.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parents[1]
RUN = AREA / 'run-001'


def child(folder, fault):
    import importlib.util
    import io
    import unittest
    sys.path.insert(0, str(folder / 'Lib'))
    for name in ('urllib.parse', 'urllib'):
        sys.modules.pop(name, None)
    import urllib.parse as parser
    assert Path(parser.__file__).resolve() == (folder/'Lib/urllib/parse.py').resolve()
    original = parser._NetlocResultMixinBase.port

    class DifferentValueError(ValueError):
        pass

    def altered_port(value):
        try:
            return original.fget(value)
        except ValueError as error:
            kind = 'bytes' if isinstance(value.netloc, bytes) else 'str'
            if fault in (kind, 'all'):
                raise DifferentValueError(*error.args) from None
            raise

    if fault != 'none':
        parser._NetlocResultMixinBase.port = property(altered_port)
    spec = importlib.util.spec_from_file_location('review_saved_tests', folder/'Lib/test/test_urlparse.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(module))
    print(json.dumps(dict(fault=fault, tests=result.testsRun,
        successful=result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), output=stream.getvalue()), ensure_ascii=True))
    return 0 if result.wasSuccessful() else 1


def prose_child(folder):
    sys.path.insert(0, str(folder / 'Lib'))
    for name in ('urllib.parse', 'urllib'):
        sys.modules.pop(name, None)
    import urllib.parse as parser
    assert Path(parser.__file__).resolve() == (folder/'Lib/urllib/parse.py').resolve()
    rows=[]
    for api in (parser.urlparse, parser.urlsplit):
        for text in ('http://example.com:70000/', 'http://example.com:[/',
                     'http://example.com:\uff0f/'):
            row=dict(api=api.__name__, input=text)
            try:
                value=api(text)
            except Exception as error:
                row.update(stage='construction', type=type(error).__name__, args=error.args)
            else:
                try:
                    row.update(stage='port_access', result=value.port)
                except Exception as error:
                    row.update(stage='port_access', type=type(error).__name__, args=error.args)
            rows.append(row)
    print(json.dumps(rows, ensure_ascii=True))
    return 0


def proposals_child(folder):
    import doctest
    import io
    sys.path.insert(0, str(folder/'Lib'))
    for name in ('urllib.parse','urllib'):
        sys.modules.pop(name,None)
    import urllib.parse as parser
    assert Path(parser.__file__).resolve()==(folder/'Lib/urllib/parse.py').resolve()
    candidates={}
    for snapshot in [RUN/'starting-candidate.json', *sorted((RUN/'after').glob('*-candidate.json'))]:
        saved=json.loads(snapshot.read_text(encoding='utf-8'))
        candidates[saved['candidate_id']]={f['path']:f['content_utf8'] for f in saved['files']}
    rows=[]
    for reply in sorted((RUN/'calls').glob('*-reply.json')):
        data=json.loads(reply.read_text(encoding='utf-8'))
        op=data.get('operation') or {}
        if op.get('action')!='patch' or op.get('path')!='Doc/library/urllib.parse.rst':
            continue
        text=op['new']
        original=candidates[op['expected_candidate_id']][op['path']]
        locations=[]
        offset=0
        while (offset:=original.find(op['old'],offset))>=0:
            locations.append(original[:offset].count('\n')+1)
            offset+=1
        # Inspect the explicitly emitted replacement fragment in isolation; never
        # pick an ambiguous match or apply it to the actor candidate.
        stream=io.StringIO()
        trial=doctest.DocTestParser().get_doctest(text,{},reply.stem,str(reply),0)
        outcome=doctest.DocTestRunner().run(trial,out=stream.write)
        rows.append(dict(call=reply.name.split('-')[0], candidate_id=op['expected_candidate_id'],
            file_sha256=sha256(original.encode()).hexdigest(),old_sha256=sha256(op['old'].encode()).hexdigest(),
            old_match_count=len(locations),old_match_start_lines=locations,
            fragment_sha256=sha256(text.encode()).hexdigest(),
            attempted=outcome.attempted, failed=outcome.failed, output=stream.getvalue()))
    print(json.dumps(rows,ensure_ascii=True))
    return 0


def main():
    args=argparse.ArgumentParser()
    args.add_argument('--child', choices=('none','str','bytes','all','prose','proposals'))
    args.add_argument('--folder', type=Path)
    args.add_argument('--snapshot', type=Path)
    args.add_argument('--output', default='artifact-probe-001')
    opts=args.parse_args()
    if opts.child:
        if opts.child=='prose':
            return prose_child(opts.folder)
        if opts.child=='proposals':
            return proposals_child(opts.folder)
        return child(opts.folder,opts.child)
    assert (RUN/'RESPONSE_SEAL.json').exists(), 'execute only after frozen run closes'
    snapshot=opts.snapshot or RUN/('final-candidate.json' if (RUN/'final-candidate.json').exists() else 'stopped-candidate.json')
    evidence=json.loads(snapshot.read_text(encoding='utf-8'))
    out=AREA/'review'/opts.output
    out.mkdir(exist_ok=False)
    folder=out/'candidate'
    identities={}
    for item in evidence['files']:
        path=folder/item['path']
        assert path.resolve().is_relative_to(folder.resolve())
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=item['content_utf8'].encode()
        assert sha256(raw).hexdigest()==item['sha256']
        path.write_bytes(raw)
        identities[item['path']]=dict(sha256=sha256(raw).hexdigest(),size_bytes=len(raw))
    rows=[]
    for fault in ('none','bytes','str','all','prose','proposals'):
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),
            '--child',fault,'--folder',str(folder.resolve())],capture_output=True,timeout=120)
        (out/(fault+'-stdout.bin')).write_bytes(result.stdout)
        (out/(fault+'-stderr.bin')).write_bytes(result.stderr)
        rows.append(dict(case=fault,returncode=result.returncode,
            stdout_sha256=sha256(result.stdout).hexdigest(),stderr_sha256=sha256(result.stderr).hexdigest(),
            result=json.loads(result.stdout)))
    report=dict(scope=__doc__,source_snapshot=str(snapshot.relative_to(AREA)),
        source_snapshot_sha256=sha256(snapshot.read_bytes()).hexdigest(),candidate_id=evidence['candidate_id'],
        files=identities,executions=rows)
    (out/'RESULTS.json').write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps([dict(case=r['case'],returncode=r['returncode'],
        successful=r['result'].get('successful')) if isinstance(r['result'],dict)
        else dict(case=r['case'],observations=len(r['result'])) for r in rows],indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
