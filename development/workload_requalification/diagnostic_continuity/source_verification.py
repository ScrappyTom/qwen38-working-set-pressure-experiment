"""Bounded parallel full hashing. No metadata cache or skipped verification."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from working_set_exp.jsonutil import sha256_file


def verify_sources(root, values, *, workers=4):
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError('unsupported verifier concurrency')
    rows = list(values.items())
    root = Path(root)

    def verify(row):
        name, expected = row
        try:
            actual = sha256_file(root / name)
            return None if actual == expected else 'source changed: ' + name
        except OSError as error:
            return f'source unavailable: {name} ({type(error).__name__})'

    # Every submitted verification completes. Error selection follows manifest
    # order rather than thread completion order; no mismatch is silently skipped.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        errors = list(pool.map(verify, rows))
    for error in errors:
        if error is not None:
            raise RuntimeError(error)
