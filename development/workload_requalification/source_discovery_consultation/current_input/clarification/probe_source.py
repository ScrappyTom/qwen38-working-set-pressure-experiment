"""Reviewer evidence from the exact saved library, not an actor correction."""
import ast
import json
from pathlib import Path
import types

AREA=Path(__file__).resolve().parent
ROOT=AREA.parents[4]
snapshot=json.loads((ROOT/'development/workload_requalification/interpolation_completion/run-002/starting-candidate.json').read_bytes())
row=next(r for r in snapshot['files'] if r['path']=='Lib/configparser.py')
source=row['content_utf8']
tree=ast.parse(source)
definitions=[]
for name in ('Error','InterpolationError','InterpolationMissingOptionError'):
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
    definitions.append(dict(name=name,start_line=node.lineno,end_line=node.end_lineno,
                            content=ast.get_source_segment(source,node)))
library=types.ModuleType('exact_review_configparser')
exec(compile(source,'Lib/configparser.py','exec'),library.__dict__)
observations=[]
for mode,policy,raw in [('basic',library.BasicInterpolation(),'%(missing)s'),
                      ('extended',library.ExtendedInterpolation(),'${missing}'),
                      ('cross_section',library.ExtendedInterpolation(),'${absent:missing}')]:
    parser=library.ConfigParser(interpolation=policy)
    parser.read_dict({'section':{'option':raw}})
    try:
        parser.get('section','option')
    except library.InterpolationMissingOptionError as error:
        observations.append(dict(mode=mode,args=list(error.args),message=error.message,
                                 rendered=str(error),tuple_rendered=str(error.args)))
        assert str(error)==error.message and str(error)!=str(error.args)
    else: raise AssertionError('Expected real missing-reference error')
result=dict(classification='Reviewer-only exact-library evidence; no task edit or check credit',
    candidate_id=snapshot['candidate_id'],path=row['path'],file_sha256=row['sha256'],
    definitions=definitions,real_lookup_observations=observations)
with (AREA/'SOURCE_FACTS.json').open('x',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
