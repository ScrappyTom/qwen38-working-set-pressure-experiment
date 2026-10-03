import functools
import typing
import unittest
from abc import ABC


class LateVirtualRegistration(unittest.TestCase):
    """Regressions for late virtual subclass registration with union
    dispatchers."""

    def test_pep604_union_late_virtual_registration(self):
        """PEP 604 union (A | B) with late virtual subclass registration."""

        class PluginBase(ABC):
            pass

        class Payload:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(PluginBase | int)
        def union_handler(x):
            return "union"

        p = Payload()
        # Before virtual registration, Payload dispatches to the default.
        self.assertEqual(handler(p), "default")
        # int member still dispatches to the union handler.
        self.assertEqual(handler(1), "union")

        # Late virtual registration: Payload becomes a virtual subclass
        # of PluginBase.  No manual cache-clear is called.
        PluginBase.register(Payload)

        # The same Payload instance must now reach the union handler.
        self.assertEqual(handler(p), "union")
        # int still works.
        self.assertEqual(handler(1), "union")

    def test_typing_union_late_virtual_registration(self):
        """typing.Union[A, B] with late virtual subclass registration."""

        class PluginBase(ABC):
            pass

        class Payload:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[PluginBase, int])
        def union_handler(x):
            return "union"

        p = Payload()
        self.assertEqual(handler(p), "default")
        self.assertEqual(handler(1), "union")

        PluginBase.register(Payload)

        self.assertEqual(handler(p), "union")
        self.assertEqual(handler(1), "union")

    def test_pep604_overlapping_unrelated_abcs(self):
        """A | B: virtual subclass of two unrelated ABCs raises RuntimeError."""
        class AlphaBase(ABC):
            pass
        class BetaBase(ABC):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(AlphaBase | BetaBase)
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        # First virtual registration: single ABC match, no ambiguity.
        AlphaBase.register(Concrete)
        self.assertEqual(handler(c), "union")

        # Second virtual registration: two unrelated ABCs now match.
        BetaBase.register(Concrete)
        with self.assertRaises(RuntimeError) as ctx:
            handler(c)
        self.assertEqual(
            str(ctx.exception),
            f"Ambiguous dispatch: {AlphaBase} or {BetaBase}",
        )

    def test_typing_union_overlapping_unrelated_abcs(self):
        """typing.Union[A, B]: same overlapping unrelated scenario."""
        class AlphaBase(ABC):
            pass
        class BetaBase(ABC):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[AlphaBase, BetaBase])
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        AlphaBase.register(Concrete)
        self.assertEqual(handler(c), "union")

        BetaBase.register(Concrete)
        with self.assertRaises(RuntimeError) as ctx:
            handler(c)
        self.assertEqual(
            str(ctx.exception),
            f"Ambiguous dispatch: {AlphaBase} or {BetaBase}",
        )

    def test_pep604_subclass_related_abcs(self):
        """A | B: subclass-related ABCs do not raise; more specific wins."""
        class Base(ABC):
            pass
        class Sub(Base):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(Sub | Base)
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        Sub.register(Concrete)
        self.assertEqual(handler(c), "union")

        Base.register(Concrete)
        self.assertEqual(handler(c), "union")

    def test_typing_union_subclass_related_abcs(self):
        """typing.Union[A, B]: subclass-related ABCs, no ambiguity."""
        class Base(ABC):
            pass
        class Sub(Base):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[Sub, Base])
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        Sub.register(Concrete)
        self.assertEqual(handler(c), "union")

        Base.register(Concrete)
        self.assertEqual(handler(c), "union")

    def test_pep604_explicit_registration_resolves_ambiguity(self):
        """Explicit registration of the concrete type overrides ambiguous MRO."""
        class AlphaBase(ABC):
            pass
        class BetaBase(ABC):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(AlphaBase | BetaBase)
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        AlphaBase.register(Concrete)
        BetaBase.register(Concrete)

        with self.assertRaises(RuntimeError):
            handler(c)

        @handler.register(Concrete)
        def concrete_handler(x):
            return "concrete"

        self.assertEqual(handler(c), "concrete")

    def test_typing_union_explicit_registration_resolves_ambiguity(self):
        """typing.Union: explicit registration resolves ambiguity."""
        class AlphaBase(ABC):
            pass
        class BetaBase(ABC):
            pass
        class Concrete:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[AlphaBase, BetaBase])
        def union_handler(x):
            return "union"

        c = Concrete()
        self.assertEqual(handler(c), "default")

        AlphaBase.register(Concrete)
        BetaBase.register(Concrete)

        with self.assertRaises(RuntimeError):
            handler(c)

        @handler.register(Concrete)
        def concrete_handler(x):
            return "concrete"

        self.assertEqual(handler(c), "concrete")





if __name__ == "__main__":
    unittest.main()
