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
