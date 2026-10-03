Union dispatch and virtual registration
======================================

The ``functools.singledispatch`` decorator supports registering handler
implementations for unions of concrete types.  Both PEP 604 syntax
(``A | B``) and ``typing.Union[A, B]`` are recognised.  A union handler
matches whenever the dispatch type is, or is a subclass of, any member of
the union, but it does not displace a separately registered handler for a
more specific type.  Normal ``singledispatch`` specificity rules still
apply: a handler registered directly for a subclass is preferred over a
union handler that only covers a superclass of that subclass.

Union registration
------------------

>>> import functools
>>> from abc import ABC
>>>
>>> class PluginBase(ABC):
...     pass
>>>
>>> class Payload:
...     pass
>>>
>>> @functools.singledispatch
... def handler(x):
...     return "default"
>>>
>>> @handler.register(PluginBase | int)
... def union_handler(x):
...     return "union"
>>>
>>> handler(42)
'union'
>>> handler("hello")
'default'

More-specific dispatch still applies
------------------------------------

A union handler does not override a handler registered for a concrete
subclass that is more specific than any member of the union:

>>> @handler.register(bool)
... def bool_handler(x):
...     return "bool"
>>>
>>> handler(True)
'bool'
>>> handler(42)
'union'

Late virtual registration
-------------------------

When a class is registered as a *virtual* subclass of a union member after
instances of that class have already been dispatched, the next dispatcher
call transparently picks up the new relationship.  No manual cache clear is
required:

>>> p = Payload()
>>> handler(p)
'default'
>>>
>>> PluginBase.register(Payload)
<class '__main__.Payload'>
>>>
>>> handler(p)
'union'
>>> handler(42)
'union'

The dispatcher tracks the ``abc`` cache token internally.  When the token
changes (as it does when ``ABCMeta.register`` mutates the ABC cache),
stale dispatch-cache entries are discarded on the next call.

Limitation: parameterized generics
----------------------------------

Union members must be concrete runtime classes (instances of ``type``).
Parameterized generic aliases such as ``list[int]`` are **not** valid union
members and are rejected at registration time:

>>> try:
...     @handler.register(PluginBase | list[int])
...     def bad(x):
...         pass
... except TypeError as exc:
...     print(exc)
Invalid union member list[int]: must be a runtime class