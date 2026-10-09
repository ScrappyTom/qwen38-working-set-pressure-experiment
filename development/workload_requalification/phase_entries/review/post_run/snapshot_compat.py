"""Evaluator-only compatibility for integer diff keys after JSON decoding.

The frozen snapshot writer sorts integer keys numerically; JSON readers return
string keys. Restoring the exact same map then sorts it lexically for comparison.
Restore the in-memory key type without changing any key identity or diff bytes.
The original restore checks and complete replay remain in force.
"""
import copy
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def restored_diff_keys(task_class):
    original = task_class.restore

    def restore(self, state, *args, **kwargs):
        converted = copy.deepcopy(state)
        diffs = state['diffs']
        normalized = {}
        for key, value in diffs.items():
            if type(key) is int:
                number = key
            elif isinstance(key, str) and key.isascii() and key.isdecimal() and str(int(key)) == key:
                number = int(key)
            else:
                raise ValueError('noncanonical diff sequence key')
            if number < 1 or number in normalized:
                raise ValueError('invalid or duplicate diff sequence key')
            normalized[number] = value
        converted['diffs'] = normalized
        return original(self, converted, *args, **kwargs)

    with patch.object(task_class, 'restore', restore):
        yield
