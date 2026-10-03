"""Evaluator-only engineering specimens, never selected for actor input."""
import textwrap

REGISTER = '''    def _is_union_type(cls):
        from typing import get_origin, Union
        return get_origin(cls) in (Union, types.UnionType)

    def _dispatch_members(cls):
        if isinstance(cls, type):
            return (cls,)
        if _is_union_type(cls):
            from typing import get_args
            members = get_args(cls)
            if all(isinstance(member, type) for member in members):
                return members
        return None

    def register(cls, func=None):
        """Register an implementation for a class or a union of classes."""
        nonlocal cache_token
        members = _dispatch_members(cls)
        if members is not None:
            if func is None:
                return lambda f: register(cls, f)
        else:
            if func is not None:
                raise TypeError(f"Invalid first argument to `register()`: {cls!r}")
            ann = getattr(cls, '__annotations__', {})
            if not ann:
                raise TypeError(
                    f"Invalid first argument to `register()`: {cls!r}. "
                    f"Use either `@register(some_class)` or plain `@register` "
                    f"on an annotated function."
                )
            func = cls
            from typing import get_type_hints
            argname, cls = next(iter(get_type_hints(func).items()))
            members = _dispatch_members(cls)
            if members is None:
                if _is_union_type(cls):
                    raise TypeError(f"Invalid annotation for {argname!r}. "
                                    f"{cls!r} not all arguments are classes.")
                raise TypeError(f"Invalid annotation for {argname!r}. "
                                f"{cls!r} is not a class.")
        for member in members:
            registry[member] = func
        if cache_token is None and any(hasattr(member, '__abstractmethods__') for member in members):
            cache_token = get_cache_token()
        dispatch_cache.clear()
        return func

'''


def library_replacement(delivered_text):
    first = delivered_text.index('    def register(cls, func=None):')
    last = delivered_text.index('    def wrapper(*args, **kw):', first)
    return delivered_text[:first] + REGISTER + delivered_text[last:]


UNION_TESTS = '''import functools
import typing
import unittest


class UnionRegistrationTests(unittest.TestCase):
    def test_explicit_forms(self):
        for union in (typing.Union[int, str], int | str):
            @functools.singledispatch
            def dispatch(value): return 'default'
            def handler(value): return 'union'
            self.assertIs(dispatch.register(union, handler), handler)
            self.assertEqual([dispatch(1), dispatch('x'), dispatch([])], ['union', 'union', 'default'])
            self.assertIs(dispatch.registry[int], handler)
            self.assertIs(dispatch.registry[str], handler)

    def test_decorator_forms(self):
        for union in (typing.Union[int, str], int | str):
            @functools.singledispatch
            def dispatch(value): return 'default'
            @dispatch.register(union)
            def handler(value): return 'union'
            self.assertEqual([dispatch(1), dispatch('x')], ['union', 'union'])

    def test_inferred_forms(self):
        for union in (typing.Union[int, str], int | str):
            @functools.singledispatch
            def dispatch(value): return 'default'
            def handler(value): return 'union'
            handler.__annotations__ = {'value': union}
            dispatch.register(handler)
            self.assertEqual([dispatch(1), dispatch('x')], ['union', 'union'])

    def test_invalid_union_is_atomic(self):
        for union in (typing.Union[int, list[str]], int | list[str]):
            @functools.singledispatch
            def dispatch(value): return 'default'
            def handler(value): return 'union'
            before = dict(dispatch.registry)
            with self.assertRaises(TypeError): dispatch.register(union, handler)
            self.assertEqual(dict(dispatch.registry), before)
'''

DYNAMIC_TESTS = '''import abc
import functools
import typing
import unittest


class DynamicRegistrationTests(unittest.TestCase):
    def exercise(self, style):
        class Plugin(abc.ABC): pass
        class Payload: pass
        union = typing.Union[Plugin, int] if style == 'typing' else Plugin | int
        @functools.singledispatch
        def dispatch(value): return 'default'
        @dispatch.register(union)
        def handler(value): return 'plugin'
        self.assertEqual(dispatch(Payload()), 'default')
        Plugin.register(Payload)
        self.assertTrue(issubclass(Payload, Plugin))
        self.assertEqual(dispatch(Payload()), 'plugin')
        self.assertEqual(dispatch(1), 'plugin')
    def test_typing_union(self): self.exercise('typing')
    def test_pep604_union(self): self.exercise('pep604')
'''

DOC = '''Union dispatch and virtual registration
======================================

A union registration assigns the same handler to each runtime class member.
Both ``typing.Union`` and ``|`` unions are supported. Parameterized generics such
as ``list[str]`` are not runtime dispatch classes and are rejected as members.
The registry contains the member classes, rather than a new union dispatch key.

    >>> import functools, typing
    >>> @functools.singledispatch
    ... def describe(value):
    ...     return 'default'
    >>> @describe.register(typing.Union[int, str])
    ... def describe_scalar(value):
    ...     return 'scalar'
    >>> describe(3), describe('x'), describe([])
    ('scalar', 'scalar', 'default')

Virtual membership may change without another dispatcher registration. A cached
default must then be reconsidered. This works without manually clearing caches:

    >>> import abc
    >>> class Plugin(abc.ABC):
    ...     pass
    >>> class Payload:
    ...     pass
    >>> @functools.singledispatch
    ... def route(value):
    ...     return 'default'
    >>> @route.register(Plugin | int)
    ... def route_plugin(value):
    ...     return 'plugin'
    >>> route(Payload())
    'default'
    >>> Plugin.register(Payload) is Payload
    True
    >>> route(Payload())
    'plugin'
'''
