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

Overlapping virtual membership
-----------------------------

When a class is virtually registered as a subclass of two *unrelated*
abstract base classes in the same union, the dispatcher raises
``RuntimeError`` because it cannot select between two implicit ABC
entries that are both absent from the concrete MRO:

>>> import functools
>>> from abc import ABC
>>>
>>> class Shape(ABC):
...     pass
>>>
>>> class Style(ABC):
...     pass
>>>
>>> class Document:
...     pass
>>>
>>> @functools.singledispatch
... def overlap_handler(x):
...     return "default"
>>>
>>> @overlap_handler.register(Shape | Style)
... def union_handler(x):
...     return "union"
>>>
>>> doc = Document()
>>> overlap_handler(doc)
'default'
>>>
>>> Shape.register(Document)
<class '__main__.Document'>
>>>
>>> Style.register(Document)
<class '__main__.Document'>
>>>
>>> try:
...     overlap_handler(doc)
... except RuntimeError as exc:
...     print(exc)
Ambiguous dispatch: <class '__main__.Shape'> or <class '__main__.Style'>

``Document`` is a *virtual* subclass of both ``Shape`` and ``Style``:
the relationship lives in each ABC's internal cache, not in
``Document.__mro__``.  The composed MRO contains both as implicit
entries; because neither is a subclass of the other the dispatch
loop cannot choose and reports the ambiguity.

If the two ABCs are *related* by inheritance the more specific one
precedes the other in the composed MRO and no error is raised:

>>> class Base(ABC):
...     pass
>>>
>>> class Derived(Base):
...     pass
>>>
>>> @functools.singledispatch
... def related_handler(x):
...     return "default"
>>>
>>> @related_handler.register(Base | Derived)
... def related_union(x):
...     return "union"
>>>
>>> class Widget:
...     pass
>>>
>>> w = Widget()
>>> related_handler(w)
'default'
>>>
>>> Base.register(Widget)
<class '__main__.Widget'>
>>>
>>> Derived.register(Widget)
<class '__main__.Widget'>
>>>
>>> related_handler(w)
'union'

Here ``Derived`` is a concrete subclass of ``Base``.  The composed
MRO places ``Derived`` before ``Base``; when the loop reaches
``Base`` it sees ``issubclass(Derived, Base)`` is true and breaks,
selecting the union handler.

Registering a handler for the concrete type itself bypasses the
ambiguous MRO walk entirely, because ``dispatch`` checks
``registry[cls]`` before calling ``_find_impl``:

>>> @overlap_handler.register(Document)
... def doc_handler(x):
...     return "concrete"
>>>
>>> overlap_handler(doc)
'concrete'

Three mechanisms are at work:

* **Virtual membership** -- ``ABC.register(C)`` adds ``C`` to the
  ABC's internal cache without modifying ``C.__mro__``.  The
  composed MRO picks it up through ``issubclass`` checks, producing
  an *implicit* entry.

* **Concrete inheritance** -- ``class Child(Parent)`` puts
  ``Parent`` in ``Child.__mro__``.  A registry entry for ``Parent``
  is found as an *explicit* entry during the MRO walk.

* **Handler selection** -- ``dispatch(cls)`` tries
  ``dispatch_cache[cls]``, then ``registry[cls]``, and only then
  falls through to ``_find_impl``.  An explicit ``registry`` entry
  for the concrete type short-circuits the walk and its ambiguity
  check.