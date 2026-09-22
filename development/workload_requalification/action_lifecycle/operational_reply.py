"""Opt-in operational replies; historical decision contracts remain unchanged."""
from __future__ import annotations

import copy

from working_set_exp import decision_view, working_view


_FORMS_BEFORE = (
    'Supported forms, in displayed property order: '
    '{"discussion":string,"operation":operation}, '
    '{"discussion":string,"account":string,"operation":operation}, '
    '{"discussion":string,"account":string}, or {"discussion":string}. '
)
_FORMS_AFTER = (
    'Supported forms, in displayed property order: '
    '{"discussion":string,"operation":operation}, '
    '{"discussion":string,"account":string,"operation":operation}, '
    'or {"discussion":string,"account":string}. '
)
_TERMINATION_BEFORE = (
    'Discussion is archived and not carried into the next decision. '
    'Discussion alone ends the run; an account-only reply records the account and continues. '
)
_TERMINATION_AFTER = (
    'Discussion is archived and not carried into the next decision. '
    'An operational reply must request an operation or explicitly update the account; '
    'discussion alone is not an accepted reply. '
    'An account-only reply records the account and continues. '
)


def _narrow_schema(envelope):
    """Check the inherited outer contract before removing its one terminal form."""
    value = copy.deepcopy(envelope)
    try:
        rule = value['json_schema']['schema']
        forms = rule['oneOf']
        families = [('discussion',), ('discussion', 'operation'),
                    ('discussion', 'account'), ('discussion', 'account', 'operation')]
        if set(rule) != {'oneOf'} or len(forms) != len(families):
            raise ValueError('inherited reply forms changed')
        for form, fields in zip(forms, families):
            if (set(form) != {'type', 'properties', 'required', 'additionalProperties'}
                    or form['type'] != 'object' or form['additionalProperties'] is not False
                    or tuple(form['properties']) != fields or form['required'] != list(fields)
                    or form['properties']['discussion'] != {'type': 'string'}
                    or ('account' in fields and form['properties']['account'] != {'type': 'string'})):
                raise ValueError('inherited reply forms changed')
        if forms[1]['properties']['operation'] != forms[3]['properties']['operation']:
            raise ValueError('inherited operation forms differ by reply family')
    except (KeyError, TypeError) as error:
        raise ValueError('inherited reply forms changed') from error
    del forms[0]
    return value


def reply_schema(checks):
    return _narrow_schema(decision_view.reply_schema(checks))


def reply_grammar(checks, converter_class):
    """Reuse the inherited literal channel and grammar assembly, narrowing only JSON."""
    inherited = decision_view.reply_schema(checks)
    narrowed = _narrow_schema(inherited)
    replacements = []

    class OperationalConverter(converter_class):
        def visit(self, schema, name):
            if name == 'ordinary-reply':
                if schema != inherited['json_schema']['schema'] or replacements:
                    raise ValueError('inherited ordinary grammar entry changed')
                replacements.append(name)
                schema = narrowed['json_schema']['schema']
            return super().visit(schema, name)

    grammar = decision_view.reply_grammar(checks, OperationalConverter)
    if replacements != ['ordinary-reply']:
        raise ValueError('inherited ordinary grammar entry was not narrowed')
    return grammar


def validate_reply(reply, checks):
    working_view.validate(reply, reply_schema(checks)['json_schema']['schema'])


def decode_reply(content, checks):
    reply = decision_view.decode_reply(content)
    validate_reply(reply, checks)
    return reply


def operating_reference(existing_text):
    """Replace only the source-checked outer forms and terminal prose."""
    for before, after in ((_FORMS_BEFORE, _FORMS_AFTER),
                          (_TERMINATION_BEFORE, _TERMINATION_AFTER)):
        if existing_text.count(before) != 1:
            raise ValueError('inherited operational reference changed')
        existing_text = existing_text.replace(before, after, 1)
    return existing_text
