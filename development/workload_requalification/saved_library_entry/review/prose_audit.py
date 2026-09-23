"""Reviewer-side source probes; never sent to the completed actor trajectory."""
import json
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parent
run = ROOT.parent/'run-001'
assert (run/'RESPONSE_SEAL.json').exists()
raw = json.loads((run/'final-candidate.json').read_text(encoding='utf-8'))
files = {r['path']:r['content_utf8'] for r in raw['files']}
module = types.ModuleType('reviewed_saved_configparser')
exec(compile(files['Lib/configparser.py'], 'reviewed_saved_configparser.py', 'exec'), module.__dict__)
cases = [
    ('greater_indent', '[s]\n  key\n    next\n', True, 3, '    next\n'),
    ('same_indent', '[s]\n  key\n  next\n', False, None, None),
    ('indented_comment', '[s]\nkey\n  # comment\n', False, None, None),
    ('indented_blank', '[s]\nkey\n  \n', False, None, None),
    ('no_final_newline', '[s]\nkey\n  next', True, 3, '  next'),
    ('continuation_after_blank', '[s]\nkey\n\n  next\n', True, 4, '  next\n'),
]
outcomes = []
for name, text, raised, lineno, line in cases:
    parser = module.ConfigParser(allow_no_value=True)
    try:
        parser.read_string(text, source='review-custom-source')
    except module.MultilineContinuationError as error:
        result = dict(raised=True, source=error.source, lineno=error.lineno,
                      line=error.line, args=error.args)
        assert raised and error.source == 'review-custom-source'
        assert (error.lineno, error.line) == (lineno, line)
    else:
        result = dict(raised=False)
        assert not raised
    outcomes.append(dict(case=name, input=text, observation=result))
value = dict(classification='Reviewer-side behavioral probes, not additional model performance',
    candidate=raw['candidate_id'], model_requests=0, public_checker_executions=0,
    outcomes=outcomes, findings=[
        'The trigger requires relative greater indentation and a nonempty parsed value after comment processing.',
        'Blank/comment lines do not themselves trigger the exception.',
        'The final line may lack a newline; exact line preserves its actual form.',
        'A supplied read_string source name is preserved; <string> is only the default.',
        'The added3.12 version marker is contradicted by the separately sourced official release documentation.'])
(ROOT/'PROSE_AUDIT.json').write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())
print(json.dumps(value, indent=2))
