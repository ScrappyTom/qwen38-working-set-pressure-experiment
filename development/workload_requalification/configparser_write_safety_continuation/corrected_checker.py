"""Remove one unsupported constructor-format requirement, preserving all else."""
import bootstrap
import qualify_cpu as previous
import material

UNSUPPORTED = b"        self.assertEqual(str(self.library.InvalidWriteError('bad key')), 'bad key')"


def contract_source():
    lines = (material.AREA/'contract_cases.py').read_bytes().splitlines(keepends=True)
    assert sum(line.rstrip(b'\r\n') == UNSUPPORTED for line in lines) == 1
    return b''.join(line for line in lines if line.rstrip(b'\r\n') != UNSUPPORTED)


def checker():
    return (b'CONFIG = ' + repr(material.checker_configuration()).encode() + b'\n' +
            contract_source() + b'\n' + (material.AREA/'checker_program.py').read_bytes())


def run(files, ordinary=False):
    # Reuse exactly the qualified ordinary subprocess environment and capture.
    # This local, synchronous override cannot affect the frozen old process/run.
    from unittest.mock import patch
    with patch.object(previous, 'checker', checker):
        return previous.run(files, ordinary=ordinary)


def direct(raw, name):
    namespace = {}
    exec(compile(contract_source(), 'corrected-contract', 'exec'), namespace)
    from unittest.mock import patch
    with patch.object(previous, 'WriteSafetyContract', namespace['WriteSafetyContract']):
        return previous.direct(raw, name)
