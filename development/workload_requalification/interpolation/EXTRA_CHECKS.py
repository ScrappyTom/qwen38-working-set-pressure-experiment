"""Declared additional checks; executed after the preserved legacy computation."""

def restoration_assertions():
    """Change one restored value only, by actual lookup mode and transport."""
    kind = parser.InterpolationMissingOptionError
    policies = (parser.BasicInterpolation, parser.ExtendedInterpolation)
    modes = ('copy', 'deepcopy', *(f'pickle:{p}' for p in range(pickle.HIGHEST_PROTOCOL + 1)))
    results = {}
    class WrongRestoredClass(kind):
        pass
    for fault in ('restored_class', 'restored_diagnostic'):
        targets = []
        for policy in policies:
            for mode in modes:
                known, holds, pending = {}, [], {}
                original = copy.copy, copy.deepcopy, pickle.dumps, pickle.loads
                getters = {p:p.before_get for p in policies}
                def wrap_get(p):
                    def get(self, *args, **kwargs):
                        try:
                            return getters[p](self, *args, **kwargs)
                        except kind as error:
                            known[id(error)] = p
                            holds.append(error)
                            raise
                    return get
                def corrupt(value, source_policy, transport):
                    if isinstance(value, kind) and source_policy is policy and transport == mode:
                        if fault == 'restored_class':
                            return WrongRestoredClass(*value.args)
                        value.message += ' [injected diagnostic fault]'
                    return value
                def shallow(obj, *args, **kwargs):
                    return corrupt(original[0](obj, *args, **kwargs), known.get(id(obj)), 'copy')
                def deep(obj, *args, **kwargs):
                    return corrupt(original[1](obj, *args, **kwargs), known.get(id(obj)), 'deepcopy')
                def dumps(obj, protocol=None, *args, **kwargs):
                    data = original[2](obj, protocol, *args, **kwargs)
                    if id(obj) in known:
                        n = pickle.DEFAULT_PROTOCOL if protocol is None else protocol
                        pending[data] = (known[id(obj)], pickle.HIGHEST_PROTOCOL if n < 0 else n)
                    return data
                def loads(data, *args, **kwargs):
                    value = original[3](data, *args, **kwargs)
                    p, n = pending.get(data, (None, None))
                    return corrupt(value, p, f'pickle:{n}')
                for p in policies:
                    p.before_get = wrap_get(p)
                copy.copy, copy.deepcopy, pickle.dumps, pickle.loads = shallow, deep, dumps, loads
                try:
                    observation = run_suite(added_suite('declared_' + fault))
                finally:
                    for p in policies:
                        p.before_get = getters[p]
                    copy.copy, copy.deepcopy, pickle.dumps, pickle.loads = original
                targets.append(dict(target=dict(policy=policy.__name__, transport=mode),
                    detected=bool(observation['tests'] and not observation['successful']),
                    execution=observation))
        results[fault] = dict(tests=sum(t['execution']['tests'] for t in targets),
            successful=all(t['execution']['successful'] for t in targets),
            all_targets_detected=all(t['detected'] for t in targets), targets=targets)
    return results


legacy_report = report
observed = dict(legacy_report['observed_paths'])
observed['missing_paths'] = []
for policy in ('BasicInterpolation', 'ExtendedInterpolation'):
    for mode in ('copy', 'deepcopy', *(f'pickle:{p}' for p in range(pickle.HIGHEST_PROTOCOL + 1))):
        if mode not in observed['modes'][policy]:
            observed['missing_paths'].append(dict(policy=policy, operation=mode,
                lookup='real missing reference; cross-section for ExtendedInterpolation'))
    for key in ('raw_bypass','resolved'):
        if policy not in observed[key]:
            observed['missing_paths'].append(dict(policy=policy, operation=key))
assert observed['complete'] == (not observed['missing_paths'])
ordinary = all(legacy_report[k]['successful'] for k in
    ('saved_suite', 'edited_suite', 'backport_contract', 'observed_paths'))
faults = {**legacy_report['restoration_faults'], **restoration_assertions()}
helper_namespace = {}
exec(compile(_EXAMPLES_HELPER, 'preserved_example_runner.py', 'exec'), helper_namespace)
examples = helper_namespace['check_added_examples'](_SAVED_FILES[doc_path], doc, doc_path)
tests_ok = bool(preserved and added and ordinary and legacy_report['observed_paths']['complete']
    and all(r['tests'] and not r['successful'] for r in legacy_report['restoration_faults'].values())
    and all(faults[n]['all_targets_detected'] for n in ('restored_class','restored_diagnostic')))
public_ok = legacy_report['passed'] and tests_ok and examples['successful']
report = dict(observation_schema='contribution-check-v2', scope=_SCOPE,
    existing_work_preserved=preserved,
    documentation_preserved=all(op[0] in ('equal','insert') for op in doc_change.get_opcodes()),
    saved_suite=legacy_report['saved_suite'], edited_suite=legacy_report['edited_suite'],
    observed_paths=observed, fault_sensitivity=faults,
    backport_contract=legacy_report['backport_contract'], added_tests=sorted(added),
    legacy_public_passed=legacy_report['passed'], legacy_report=legacy_report,
    passed=tests_ok if _SCOPE == 'tests' else examples['successful'] if _SCOPE == 'examples' else public_ok)
if _SCOPE in ('public', 'examples'):
    report['examples'] = examples
if _SCOPE == 'examples':
    report = {k:v for k,v in report.items() if k in
        ('observation_schema','scope','examples','passed','legacy_report')}
print(json.dumps(report, ensure_ascii=True, separators=(',',':')))
raise SystemExit(0 if report['passed'] else 1)
