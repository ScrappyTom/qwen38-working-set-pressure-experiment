"""Independent artifact probes, never run feedback or reference work for the actor."""
import argparse
import abc
import _abc
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import overlap_task as entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('condition', choices=('control','current_job'))
    parser.add_argument('--version', default='003')
    args = parser.parse_args()
    task = entry.Task(args.condition,args.version)
    seal = entry.read(task.RUN/'RESPONSE_SEAL.json')
    stem = 'stopped' if seal['disposition']=='stopped_without_retry' else 'final'
    candidate = entry.study.candidate_from_snapshot(entry.read(task.RUN/f'{stem}-candidate.json'))
    output = entry.HERE/'review'/f'contract-probe-{args.condition}-{args.version}'
    assert not output.exists(), 'Preserve prior probe'
    output.mkdir()
    env = {'__name__':'independent_contract_probe'}
    exec(compile(entry.checker(task.inherited_candidate), '<frozen-checker-functions>', 'exec'),env)
    source = candidate.file_map['Lib/functools.py'].decode()
    test_source = candidate.file_map[entry.TEST].decode()
    guard = 'raise RuntimeError("Ambiguous dispatch: {} or {}".format(\n                    match, t))'
    assert source.count(guard)==1
    variants = {
        'unchanged': source,
        'silent_selection': source.replace(guard,'return registry[match]',1),
        'exception_subclass': source.replace(guard,
            'raise type("RuntimeErrorSubclass", (RuntimeError,), {})("Ambiguous dispatch: {} or {}".format(\n                    match, t))',1),
        'wrong_diagnostic_suffix': source.replace(guard,
            'raise RuntimeError("Ambiguous dispatch: {} or {} [fault]".format(\n                    match, t))',1),
    }
    facts = dict(condition=args.condition, candidate_id=candidate.candidate_id,
        seal_sha256=hashlib.sha256((task.RUN/'RESPONSE_SEAL.json').read_bytes()).hexdigest(),
        purpose='Independent sensitivity review; not recorded actor feedback or new model evidence',
        original_registered_checker_unchanged=True, results={})
    class RegisteredABC(abc.ABC): pass
    class RegisteredValue: pass
    RegisteredABC.register(RegisteredValue)
    def cache_state():
        registry, positive, negative, version = _abc._get_dump(RegisteredABC)
        return dict(registered=any(r() is RegisteredValue for r in registry),
            positive_cached=any(r() is RegisteredValue for r in positive),
            negative_cached=any(r() is RegisteredValue for r in negative),
            negative_cache_version=version)
    after_registration = cache_state()
    membership = issubclass(RegisteredValue, RegisteredABC)
    after_query = cache_state()
    _abc._reset_caches(RegisteredABC)
    after_cache_reset = cache_state()
    facts['abc_registration_observation'] = dict(python=sys.version,
        after_registration=after_registration, membership=membership,
        after_membership_query=after_query, after_cache_reset=after_cache_reset,
        membership_after_cache_reset=issubclass(RegisteredValue, RegisteredABC),
        source='https://github.com/python/cpython/blob/v3.11.9/Modules/_abc.c',
        meaning='Registration is retained in the registry independently of derived subclass caches; this is a separate prose probe, not actor feedback.')
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        tests = folder/'actor_tests.py'
        tests.write_text(test_source,encoding='utf-8')
        for kind, body in variants.items():
            path = folder/f'library_{kind}.py'
            path.write_text(body,encoding='utf-8')
            library = env['load_library'](path,f'independent_library_{kind}')
            result = env['suite_result'](env['new_actor_suite'](tests,library,f'independent_actor_{kind}'))
            facts['results'][kind] = result
            (output/f'{kind}-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        tree = ast.parse(test_source)
        old = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LateVirtualRegistration')
        extra = [n for n in tree.body if isinstance(n,ast.ClassDef) and n.name!='LateVirtualRegistration']
        if extra:
            # A legitimate alternate organization: append exactly the new methods
            # inside the old class, retaining all old methods and the main guard.
            lines = test_source.splitlines(keepends=True)
            methods = [n for cls in extra for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
            inserted = '\n'+''.join(''.join(lines[n.lineno-1:n.end_lineno])+'\n' for n in methods)
            text = ''.join(lines[:old.end_lineno])+inserted+''.join(lines[old.end_lineno:extra[0].lineno-1])
            text += ''.join(lines[extra[-1].end_lineno:])
            ast.parse(text)
            tests.write_text(text,encoding='utf-8')
            (output/'legitimate-methods-in-old-class.py').write_text(text,encoding='utf-8')
            path = folder/'library_unmodified.py'
            path.write_text(source,encoding='utf-8')
            library = env['load_library'](path,'independent_method_organization')
            all_tests = env['suite_result'](env['actor_suite'](tests,library,'independent_all_methods'))
            counted = env['suite_result'](env['new_actor_suite'](tests,library,'independent_counted_methods'))
            prefix,suffix = task.inherited_candidate.file_map[entry.TEST].split(b'\n\nif __name__ == "__main__":',1)
            raw = tests.read_bytes()
            facts['legitimate_existing_class'] = dict(all_tests=all_tests,counted_new_tests=counted,
                earlier_byte_prefix_preserved=raw.startswith(prefix),
                main_guard_preserved=raw.endswith(b'\n\nif __name__ == "__main__":'+suffix))
    (output/'PROBE.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(condition=args.condition, results={k:{a:v[a] for a in ('tests','failures','errors','passed')} for k,v in facts['results'].items()},
        legitimate_existing_class_count=facts.get('legitimate_existing_class',{}).get('counted_new_tests',{}).get('tests')),ensure_ascii=False))


if __name__=='__main__': main()
