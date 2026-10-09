import sys
import tempfile
from pathlib import Path
sys.path.insert(0, "src")
from addressable_information_layer.verifiers import MAX_COMMAND_TIMEOUT_SECONDS, _bounded_timeout, _resolve_safe_cwd, _safe_relative_path

assert _safe_relative_path("pkg/module.py").as_posix() == "pkg/module.py"
assert _safe_relative_path("../escape.py") is None
assert _safe_relative_path("/absolute.py") is None
assert _safe_relative_path("") is None
assert _bounded_timeout(0) == 1
assert _bounded_timeout(20) == 20
assert _bounded_timeout(MAX_COMMAND_TIMEOUT_SECONDS + 99) == MAX_COMMAND_TIMEOUT_SECONDS
assert _bounded_timeout("invalid") == 20
with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    assert _resolve_safe_cwd(workspace, "sub/dir").is_relative_to(workspace.resolve())
    assert _resolve_safe_cwd(workspace, "../escape") is None
print("public passed")

# Declared contract extension follows the unchanged original.
"""Declared execution-side extension; no external command or unsafe write."""
from dataclasses import asdict
from types import SimpleNamespace
from addressable_information_layer import verifiers as v
from addressable_information_layer.records import CriterionArtifact, VerifierStatus

# The original public assertions run first in the same ordinary interpreter.
for spelling in ('C:/outside.py', 'C:\\outside.py', 'C:outside.py',
                 '\\\\server\\share\\outside.py', '\\outside.py',
                 'pkg/../outside.py', 'pkg\\..\\outside.py'):
    assert v._safe_relative_path(spelling) is None, ('unsafe path accepted', spelling)
for spelling, expected in (('nested\\module.py', 'nested/module.py'),
                           ('pkg/module.py', 'pkg/module.py')):
    assert v._safe_relative_path(spelling).as_posix() == expected, ('relative path changed', spelling)
for value in (None, 'invalid', float('inf'), float('-inf'), float('nan')):
    try:
        observed = v._bounded_timeout(value)
    except Exception as error:
        raise AssertionError(('invalid timeout raised instead of defaulting to 20', repr(value), type(error).__name__)) from error
    assert observed == 20, ('invalid timeout must default to 20', repr(value), observed)
for value, expected in ((-100, 1), (0, 1), (1, 1), (20, 20),
                        (v.MAX_COMMAND_TIMEOUT_SECONDS, v.MAX_COMMAND_TIMEOUT_SECONDS),
                        (10**9, v.MAX_COMMAND_TIMEOUT_SECONDS)):
    assert v._bounded_timeout(value) == expected, ('inclusive timeout clamp', value, expected)

with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    for spelling in ('../escape', '/absolute', 'C:/outside', 'C:outside', '\\\\server\\share\\outside'):
        assert v._resolve_safe_cwd(workspace, spelling) is None, ('cwd must remain contained', spelling)
    for spelling in ('', '.', 'nested/dir'):
        cwd = v._resolve_safe_cwd(workspace, spelling)
        assert cwd is not None and cwd.is_relative_to(workspace.resolve()), ('valid cwd', spelling)
    # Only accepted canonical relative paths reach materialization. Rejected
    # unsafe spellings above are never sent to the filesystem by this checker.
    artifact = SimpleNamespace(path_or_name='nested/item.txt', text='exact material')
    v._materialize_artifacts(workspace, {'a': artifact})
    assert (workspace / 'nested/item.txt').read_text(encoding='utf-8') == 'exact material'

criterion = CriterionArtifact('qualified-check', 'preserve verifier behavior', 'command')
assert v._command_is_allowed(['python', '-m', 'pytest'], criterion)
assert not v._command_is_allowed(['python', '-c', 'pass'], criterion)
assert not v._command_is_allowed(['unlisted'], criterion)
custom = CriterionArtifact('custom', 'custom prefix', 'command', params={'allowed_prefixes': [['tool', 'check']]})
assert v._command_is_allowed(['tool', 'check', 'file'], custom)
assert not v._command_is_allowed(['tool', 'run'], custom)
first = v._receipt(criterion, VerifierStatus.PASSED, 'same observed result', None)
second = v._receipt(criterion, VerifierStatus.PASSED, 'same observed result', None)
assert asdict(first) == asdict(second), 'same inputs must produce deterministic receipts'
assert first.receipt_id != v._receipt(criterion, VerifierStatus.FAILED, 'same observed result', None).receipt_id
print('expanded verifier contract passed')

# Separately declared native composition contract follows.
"""Declared successor contract: validate path normalization and native joining."""
from pathlib import PureWindowsPath
from addressable_information_layer import verifiers as v

# No rejected spelling is materialized. Native joining below is lexical only.
unsafe_spellings = (
    'C:/outside.py', 'C:outside.py', './C:/outside.py', '.\\C:\\outside.py',
    'nested/C:/outside.py', 'nested/C:outside.py', 'nested\\C:\\outside.py',
    'nested//D:outside.py', 'nested/./D:/outside.py', './D:/outside.py',
    'D:/outside.py', 'D:outside.py', 'nested/D:/outside.py',
    '/rooted.py', '\\rooted.py', '//server/share/item.py',
    '\\\\server\\share\\item.py', '../outside.py', 'nested/../outside.py', '',
)
for spelling in unsafe_spellings:
    actual = v._safe_relative_path(spelling)
    assert actual is None, ('unsafe path component survived normalization', spelling,
                            str(actual) if actual is not None else None)

relative_controls = (
    ('pkg/module.py', 'pkg/module.py'),
    ('nested\\module.py', 'nested/module.py'),
    ('./nested/module.py', 'nested/module.py'),
    ('nested//module.py', 'nested/module.py'),
    ('.hidden/item.txt', '.hidden/item.txt'),
    ('alpha/beta/item.txt', 'alpha/beta/item.txt'),
)
for spelling, expected in relative_controls:
    actual = v._safe_relative_path(spelling)
    assert actual is not None and actual.as_posix() == expected, (
        'valid relative path changed', spelling, str(actual))
    for root in ('C:/workspace', 'D:/workspace'):
        workspace = PureWindowsPath(root)
        joined = workspace.joinpath(*actual.parts)
        assert joined.is_relative_to(workspace), ('native join left workspace', spelling, str(joined))
        assert joined == workspace / expected, ('native join changed relative destination', spelling, str(joined))
print('path composition contract passed')
