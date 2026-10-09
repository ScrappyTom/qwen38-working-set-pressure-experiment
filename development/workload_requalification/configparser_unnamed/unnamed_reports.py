"""Task-specific meanings over the existing complete-observation report adapter."""
import configparser_reports as previous


def scope(value):
    for row in value.get('criteria', value.get('entries', [])):
        if row['criterion'] == 'upstream.execution':
            row['meaning'] = 'All saved parser and write-safety tests execute on the current library.'
        if row['criterion'] == 'contract.execution':
            row['meaning'] = 'Independent unnamed-section behavior, write-safety integration and exact saved-file preservation.'
        if row['criterion'] == 'regression_detects_original':
            row['meaning'] = ('The added tests disagree with the saved library lacking this feature. '
                'Expected baseline failures/errors are comparison detection, not current failures. '
                'Missing-API errors alone do not establish meaningful assertions or behavioral coverage.')
        if row['criterion'] == 'documentation_directive_present':
            row['meaning'] = 'The new option and sentinel/error declarations are present; prose and examples still need independent review.'
    value['explanation'] = ('Current preserved, independent and authored suites must pass. '
        'The saved-library comparison is expected to fail because the feature is absent. '
        'Its failure does not certify test quality; behavioral sensitivity and documentation accuracy require direct review. '
        'Full captured observations remain recoverable.')
    return value


def assessment(store, handle, contract=None):
    return scope(previous.assessment(store, handle, contract))


overview = previous.overview


def inspect_check(store, handle, offset, contract=None):
    return scope(previous.inspect_check(store, handle, offset, contract))
