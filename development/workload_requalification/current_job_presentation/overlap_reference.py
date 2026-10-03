"""Evaluator-only reference; never included in actor task or selected sources."""
TEST_ADDITION = '''

class OverlappingVirtualMembership(unittest.TestCase):
    def exercise(self, style, related=False, explicit=False):
        class Left(ABC):
            pass
        class Right(Left if related else ABC):
            pass
        class Value:
            pass
        @functools.singledispatch
        def route(value):
            return 'default'
        union = Left | Right if style == 'pipe' else typing.Union[Left, Right]
        def shared(value):
            return 'shared'
        route.register(union, shared)
        value = Value()
        self.assertEqual(route(value), 'default')
        Left.register(Value)
        self.assertEqual(route(value), 'shared')
        Right.register(Value)
        if related:
            self.assertIs(route.dispatch(Value), shared)
            self.assertEqual(route(value), 'shared')
        else:
            with self.assertRaises(RuntimeError) as caught:
                route(value)
            self.assertIs(type(caught.exception), RuntimeError)
            self.assertEqual(str(caught.exception),
                f'Ambiguous dispatch: {Left} or {Right}')
        if explicit:
            def specific(value):
                return 'specific'
            self.assertIs(route.register(Value, specific), specific)
            self.assertIs(route.dispatch(Value), specific)
            self.assertEqual(route(value), 'specific')

    def test_unrelated_members(self):
        for style in ('pipe', 'typing'):
            with self.subTest(style=style):
                self.exercise(style)

    def test_related_members(self):
        for style in ('pipe', 'typing'):
            with self.subTest(style=style):
                self.exercise(style, related=True)

    def test_concrete_registration(self):
        for style in ('pipe', 'typing'):
            with self.subTest(style=style):
                self.exercise(style, explicit=True)
'''
DOC_ADDITION = '''

Overlapping virtual membership
------------------------------

Membership in a union does not impose an order on unrelated abstract bases.
When the value's class is a virtual subclass of two unrelated registered bases,
ordinary single dispatch refuses an ambiguous choice. This also applies when
both union members were registered to the same function. An explicit registration
for the concrete class takes precedence. Subclass-related abstract bases have a
specificity relationship and are not the same ambiguous case.

>>> class Left(ABC):
...     pass
>>> class Right(ABC):
...     pass
>>> class Value:
...     pass
>>> @functools.singledispatch
... def overlap(value):
...     return 'default'
>>> @overlap.register(Left | Right)
... def shared(value):
...     return 'shared'
>>> value = Value()
>>> overlap(value)
'default'
>>> _ = Left.register(Value)
>>> overlap(value)
'shared'
>>> _ = Right.register(Value)
>>> overlap(value)
Traceback (most recent call last):
    ...
RuntimeError: Ambiguous dispatch: <class '__main__.Left'> or <class '__main__.Right'>
>>> @overlap.register(Value)
... def concrete(value):
...     return 'concrete'
>>> overlap(value)
'concrete'
'''


def tests(source):
    marker = '\n\nif __name__ == "__main__":'
    assert source.count(marker) == 1
    return source.replace(marker, TEST_ADDITION + marker, 1)


def documentation(source): return source + DOC_ADDITION
