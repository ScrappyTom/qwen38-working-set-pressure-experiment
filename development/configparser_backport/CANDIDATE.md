# Larger-source candidate: configuration-parser maintenance

Use this as the next preparation candidate for useful work on larger source and
documentation. It is a known historical backport, not a fresh independent-discovery
benchmark or an unchanged replication of Experiment 020. No model request has
been made and the live task is not yet prepared.

The actual CPython v3.12.10 implementation accepts a valueless option and ordinary
multi-line string values, but an indented continuation after a valueless option
raises `AttributeError: 'NoneType' object has no attribute 'append'`. The stored
baseline cases reproduce this against the exact downloaded source. An indented
comment following the same option is harmless. The failure has a useful bounded
maintenance contract: reject the unsupported continuation with a configuration
parsing exception carrying source and location, while preserving valid input.
Python documents a dedicated `MultilineContinuationError` for this behavior from
3.13 onward: [official contract](https://docs.python.org/3.13/library/configparser.html#configparser.MultilineContinuationError).

The donor is the tagged [CPython source](https://github.com/python/cpython/tree/v3.12.10),
preserved byte-for-byte with its complete license:

| Material | Bytes | Lines |
| --- | ---: | ---: |
| `Lib/configparser.py` | 53,789 | 1,333 |
| `Lib/test/test_configparser.py` | 87,385 | 2,142 |
| `Doc/library/configparser.rst` | 52,024 | 1,387 |
| `LICENSE` | 13,936 | 279 |

The three substantive files exceed the old per-file limit. All four files, totaling
207,134 bytes, pass the new explicit 1 MiB option with every other admission bound
unchanged. These are existing source, tests and reference documentation, with no
size padding. They are a larger module/documentation work surface, not a claim
that this four-file subset is a complete large repository.

The first donor screen downloaded these exact files and reproduced the internal
error, then failed an assertion in the probe: it assumed ordinary `items()` would
return `None` for a valueless entry. Direct source and API inspection showed that
interpolated `items()` exposes an empty string, while `items(raw=True)` and `get()`
retain `None`. The failed attempt and script remain unchanged under `donor-001/`.
The separate offline continuation corrects the observation method, preserves all
four exact case outputs before checking them, and passes admission and baseline
checks under `screen-002/`. This did not require a donor patch or a model call.

The useful work should include the bounded library backport, executable regression
coverage, and the corresponding documentation update. The actor should receive the
desired behavior and incident input, with normal navigation over the larger files.
Do not supply the implementation location, replacement code or a mandatory reading
list. A correct direct repair is a valid outcome; do not force an initial mistake
or describe a publicly known maintenance issue as novel discovery.

Before exposing Qwen, finish the actual acceptance and execution preparation:

- Establish the old regression suite's dependencies and input data. The local
  Python installation omits its `test` package; the vendored suite uses
  `test.support`, `os_helper` and three `configdata` files. It has not been run.
  Do not silently substitute passing stubs or call four baseline cases a full suite.
- Check the new exception contract independently of any reference patch, including
  legitimate continuations, comments, constructor modes, reading entry points and
  source/location reporting. Keep existing behavior such as `items()` out of the
  requested change. Judge documentation against the implemented behavior.
- Qualify the actual candidate's visible reference, exact guarded edits, result
  delivery and native input admission using the existing q4/56,576, no-MTP,
  uncapped-xhigh configuration and 23,808 input ceiling. The file admission screen
  does not establish that related evidence fits together in a model call.
- Make a checked contribution available to later work and review actual use of
  that saved contribution. Record whether a real pressure boundary occurs. Do not
  manufacture one by mandatory reading, generated filler or retrospective budgets.

No new host tool, storage representation, retention policy or working account is
selected here. If preparation exposes a real delivery or capacity defect, preserve
that finding and address it before blaming model behavior. The complete larger-work
goal remains open.
