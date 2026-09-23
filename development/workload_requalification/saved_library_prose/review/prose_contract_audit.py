"""Post-run source probes of corrected prose; no model/public-check requests."""
import hashlib
import json
from pathlib import Path
import types

HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'run-001'
assert (RUN/'RESPONSE_SEAL.json').exists(), 'Only assess closed work'
raw=json.loads((RUN/'final-candidate.json').read_text(encoding='utf-8'))
files={row['path']:row['content_utf8'] for row in raw['files']}
module=types.ModuleType('review_saved_library')
exec(compile(files['Lib/configparser.py'],'review_saved_library.py','exec'),module.__dict__)
cases=[
    ('default_source','[s]\nkey\n  next\n',{},None,True,'<string>','  next\n'),
    ('custom_source_no_final_newline','[s]\nkey\n  next',{},'named-input',True,'named-input','  next'),
    ('custom_comment_prefix','[s]\nkey\n  ! comment\n',{'comment_prefixes':('!',)},None,False,None,None),
    ('blank_ends_value','[s]\nkey\n\n  next\n',{'empty_lines_in_values':False},None,False,None,None),
    ('blank_does_not_end_value','[s]\nkey\n\n  next\n',{'empty_lines_in_values':True},None,True,'<string>','  next\n'),
]
observations=[]
for name,text,options,source,raises,expected_source,expected_line in cases:
    parser=module.ConfigParser(allow_no_value=True,**options)
    try:
        if source is None: parser.read_string(text)
        else: parser.read_string(text,source=source)
    except module.MultilineContinuationError as error:
        assert raises and error.source==expected_source and error.line==expected_line
        observed=dict(raised=True,source=error.source,line=error.line,lineno=error.lineno,args=error.args)
    else:
        assert not raises
        observed=dict(raised=False,items=dict(parser.items('s')))
    observations.append(dict(case=name,input=text,options=options,source_argument=source,observed=observed))
value=dict(classification='Independent post-run source probes; not new model-performance evidence',
    candidate_id=raw['candidate_id'],observations=observations,model_requests=0,public_checker_executions=0,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    final_snapshot_sha256=hashlib.sha256((RUN/'final-candidate.json').read_bytes()).hexdigest(),
    interpretation='Blank/comment lines do not themselves raise. Their effect on a later continuation remains governed by parser configuration; the revised entry is not a full account of every setting.')
(HERE/'PROSE_CONTRACT_AUDIT.json').write_bytes((json.dumps(value,indent=2)+'\n').encode())
print(json.dumps(value,indent=2))
