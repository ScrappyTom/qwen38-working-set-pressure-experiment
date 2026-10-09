"""Reuse the qualified parser-report projection with accurate comparison scope."""
import configparser_reports as previous


def scope(value):
    for row in value.get('criteria', value.get('entries', [])):
        if row['criterion'] == 'upstream.execution':
            row['meaning'] = 'The preserved existing suite, including earlier saved multiline regressions, executes on the current library.'
        if row['criterion'] == 'regression_detects_original':
            row['meaning'] = ('New tests execute against the saved unsafe write behavior with InvalidWriteError exported. '
                'Expected comparison failures are detection, not current-library failures. '
                'The independent contract additionally requires an assertion failure, not only a missing-API error.')
    value['explanation'] = ('Current saved, independent and new suites must pass. '
        'New tests must detect the unsafe comparison implementation. '
        'The documentation declaration is mechanical; prose accuracy needs direct review. '
        'Exact complete checker streams remain recoverable.')
    return value


def assessment(store, handle, contract=None):
    return scope(previous.assessment(store, handle, contract))


overview = previous.overview


def inspect_check(store, handle, offset, contract=None):
    return scope(previous.inspect_check(store, handle, offset, contract))
