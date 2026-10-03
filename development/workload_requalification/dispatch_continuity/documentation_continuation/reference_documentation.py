"""Evaluator-only correction specimen; never included in actor entry."""


def correction(document):
    old = ('A union handler is\nselected whenever the dispatch class is, or is a subclass of, any member of\n'
           'the union.\n')
    new = ('Registration installs the handler for each member of the union.\n'
           'Normal single-dispatch precedence still applies: a more-specific\n'
           'registered class can select a different handler.\n')
    assert document.count(old) == 1
    document = document.replace(old, new, 1)
    old = ">>> PluginBase.register(Payload)\n<class 'Payload'>\n"
    assert document.count(old) == 1
    document = document.replace(old, '>>> _ = PluginBase.register(Payload)\n', 1)
    anchor = 'Late virtual registration\n-------------------------\n'
    assert document.count(anchor) == 1
    example = ('A more-specific registration takes precedence even when its class\n'
        'is a subclass of a registered union member:\n\n'
        '>>> @handler.register(bool)\n... def bool_handler(x):\n...     return "bool-specific"\n'
        '>>> handler(True)\n\'bool-specific\'\n'
        '>>> handler(42)\n\'union\'\n\n')
    document = document.replace(anchor, example + anchor, 1)
    return document.replace('unions of concrete types', 'unions of runtime classes').replace(
        'Union members must be concrete runtime classes', 'Union members must be runtime classes')
