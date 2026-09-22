"""Pinned public-only reply grammar, including actual thinking delimiter tokens."""
import argparse
import inspect
import json
from types import SimpleNamespace

import repair_task
import run_uncoached_contribution as runner
from manage import load_helper


def main(folder):
    module=repair_task.Task('artifact_map')
    harness=load_helper('small_repair_native','development/decision_interface/native.py')
    inherited=harness.cases
    def cases():
        for name,final,wanted in inherited():
            yield name,'Decide the next operation.\n</think>\n'+final,wanted
        for scope in ('public','tests','examples'):
            final=json.dumps(dict(discussion='Check.',operation=dict(action='check',check_id=scope,
                             expected_candidate_id='b'*64)))
            yield 'scope_'+scope,'</think>\n'+final,scope=='public'
        patch=dict(action='patch',path='app.py',old='old',new='new',
            expected_candidate_id='b'*64,expected_file_sha256='a'*64)
        explicit=dict(discussion='Save.',operation=patch)
        yield 'explicit_patch','</think>\n'+json.dumps(explicit),True
        unsupported={**explicit,'check_after':'public'}
        yield 'unsupported_check_after','</think>\n'+json.dumps(unsupported),False
    class Shim:
        def Task(self):return module
        def source_identities(self):return module.implementation_identities()
        def __getattr__(self,name):return getattr(module,name)
    shim=Shim();shim.runner=runner
    harness.study=shim;harness.cases=cases
    harness.decision_view=SimpleNamespace(decode_reply=lambda text:module.decode_reply(text.split('</think>',1)[1].lstrip()))
    source=inspect.getsource(harness.run).replace('False,False);assert count>=0','False,True);assert count>=0')
    namespace=dict(harness.__dict__);exec(compile(source,__file__+':qualified_harness','exec'),namespace)
    namespace['run'](repair_task.AREA/folder)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',default='native-005');main(p.parse_args().folder)
