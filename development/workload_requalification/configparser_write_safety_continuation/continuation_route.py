"""Reuse the earlier scripted route, retaining the already saved public export.

This is an evaluator-authored transition qualification, not autonomous discovery.
Its reference implementation and selected ranges never enter the operating run.
"""
from types import ModuleType
import bootstrap
import material
from working_set_exp.jsonutil import sha256_file

PATH = material.AREA/'qualification_route.py'
SOURCE = PATH.read_text(encoding='utf-8')
OLD = '''    patch(row, '"ConfigParser", "RawConfigParser"', '"InvalidWriteError", "ConfigParser", "RawConfigParser"',
          'The visible export tuple omits the exception explicitly required by the task. Add that public export; the initial check has not established working behavior.')'''
NEW = '''    assert '"InvalidWriteError"' in row['content'], 'Preserve the saved export, visible in the acquired tuple' '''
assert SOURCE.count(OLD) == 1
ADAPTED = SOURCE.replace(OLD, NEW)
route = ModuleType('saved_export_scripted_route')
route.__file__ = str(PATH)
exec(compile(ADAPTED, str(PATH), 'exec'), route.__dict__)
qualify = route.qualify
