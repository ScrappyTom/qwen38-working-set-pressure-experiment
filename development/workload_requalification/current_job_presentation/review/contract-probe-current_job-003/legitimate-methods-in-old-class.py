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

    def test_unrelated_abcs_pep604_ambiguous(self):
        """PEP 604: two unrelated ABCs raise RuntimeError on dispatch."""

        class Shape(ABC):
            pass

        class Style(ABC):
            pass

        class Document:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(Shape | Style)
        def union_handler(x):
            return "union"

        doc = Document()
        self.assertEqual(handler(doc), "default")

        Shape.register(Document)
        Style.register(Document)

        with self.assertRaises(RuntimeError) as ctx:
            handler(doc)
        self.assertEqual(
            str(ctx.exception),
            f"Ambiguous dispatch: {Shape} or {Style}"
        )

    def test_unrelated_abcs_typing_union_ambiguous(self):
        """typing.Union: two unrelated ABCs raise RuntimeError on dispatch."""

        class Shape(ABC):
            pass

        class Style(ABC):
            pass

        class Document:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[Shape, Style])
        def union_handler(x):
            return "union"

        doc = Document()
        self.assertEqual(handler(doc), "default")

        Shape.register(Document)
        Style.register(Document)

        with self.assertRaises(RuntimeError) as ctx:
            handler(doc)
        self.assertEqual(
            str(ctx.exception),
            f"Ambiguous dispatch: {Shape} or {Style}"
        )

    def test_subclass_related_abcs_pep604_no_ambiguity(self):
        """PEP 604: subclass-related ABCs do not raise."""

        class Base(ABC):
            pass

        class Derived(Base):
            pass

        class Widget:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(Base | Derived)
        def union_handler(x):
            return "union"

        w = Widget()
        self.assertEqual(handler(w), "default")

        Base.register(Widget)
        Derived.register(Widget)

        self.assertEqual(handler(w), "union")

    def test_subclass_related_abcs_typing_union_no_ambiguity(self):
        """typing.Union: subclass-related ABCs do not raise."""

        class Base(ABC):
            pass

        class Derived(Base):
            pass

        class Widget:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[Base, Derived])
        def union_handler(x):
            return "union"

        w = Widget()
        self.assertEqual(handler(w), "default")

        Base.register(Widget)
        Derived.register(Widget)

        self.assertEqual(handler(w), "union")

    def test_explicit_registration_pep604_resolves(self):
        """PEP 604: explicit registration of the concrete type resolves
        the ambiguity."""

        class Shape(ABC):
            pass

        class Style(ABC):
            pass

        class Document:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(Shape | Style)
        def union_handler(x):
            return "union"

        doc = Document()
        self.assertEqual(handler(doc), "default")

        Shape.register(Document)
        Style.register(Document)

        with self.assertRaises(RuntimeError):
            handler(doc)

        @handler.register(Document)
        def doc_handler(x):
            return "concrete"

        self.assertEqual(handler(doc), "concrete")

    def test_explicit_registration_typing_union_resolves(self):
        """typing.Union: explicit registration resolves the ambiguity."""

        class Shape(ABC):
            pass

        class Style(ABC):
            pass

        class Document:
            pass

        @functools.singledispatch
        def handler(x):
            return "default"

        @handler.register(typing.Union[Shape, Style])
        def union_handler(x):
            return "union"

        doc = Document()
        self.assertEqual(handler(doc), "default")

        Shape.register(Document)
        Style.register(Document)

        with self.assertRaises(RuntimeError):
            handler(doc)

        @handler.register(Document)
        def doc_handler(x):
            return "concrete"

        self.assertEqual(handler(doc), "concrete")





if __name__ == "__main__":
    unittest.main()
