"""Preserve transport-check observations before deriving any bounded display.

Preparation implementation only: not qualified or exposed to Qwen yet.
The caller supplies the pinned baseline files, legacy harness and task checker.
"""
import ast
from working_set_exp.jsonutil import sha256_bytes

BODY_SHA='82238dca2e1a419f8b53132ec83846bbb63ca56608320b5a3050f9bd347ad85e'
CUT_MARKER='# Keep verdicts and scopes; detailed failures remain bounded actual diagnostics.\n'
RUNNER_OLD = """def run_suite(suite):
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), successful=result.wasSuccessful(),
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)])
"""
RUNNER_NEW = """def run_suite(suite):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), successful=result.wasSuccessful(),
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)],
        runner_output=stream.getvalue())
"""


def preserve_observations(baseline_files,legacy_harness,checker_body):
    """Change stream retention/reporting, never the original acceptance predicate."""
    if sha256_bytes(checker_body)!=BODY_SHA:
        raise ValueError('unqualified transport checker body')
    harness=legacy_harness.decode('utf-8');body=checker_body.decode('utf-8')
    if harness.count(RUNNER_OLD)!=1 or body.count(CUT_MARKER)!=1:
        raise ValueError('unrecognized capture/report boundary')
    revised_harness=harness.replace(RUNNER_OLD,RUNNER_NEW)
    preserved_prefix=body.split(CUT_MARKER)[0]
    revised_body=preserved_prefix+"""# Full actual observations enter custody before bounded presentation.
result['observation_schema'] = 'exception-transport-v1'
print(json.dumps(result, ensure_ascii=True, separators=(',', ':')), flush=True)
raise SystemExit(0 if passed else 1)
"""
    # Every original instruction up to the reduction boundary stays byte-identical.
    # Also verify the public verdict expression explicitly for future maintenance.
    def verdict(source):
        return [ast.dump(n.value,include_attributes=False) for n in ast.parse(source).body
                if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='passed' for t in n.targets)]
    if verdict(body)!=verdict(revised_body) or len(verdict(body))!=1:
        raise ValueError('acceptance expression changed')
    prefix='_BASELINE_FILES = '+repr({p:b.decode('utf-8') for p,b in sorted(baseline_files.items())})+'\n'
    prefix+='_LEGACY_HARNESS_SOURCE = '+repr(revised_harness)+'\n'
    return (prefix+revised_body).encode('utf-8')
