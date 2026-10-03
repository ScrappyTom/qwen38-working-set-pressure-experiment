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


if __name__ == "__main__":
    unittest.main()
