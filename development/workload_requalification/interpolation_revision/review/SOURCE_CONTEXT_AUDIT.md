# Source-context audit of continuation C01–C06

Date: 2026-09-22. Read-only diagnostic during `run-002`; it does not change that
run, its inputs, or its allowance. No findings were supplied to Qwen. No model,
runtime, or checker was invoked for this audit. The only mechanical probe parsed
the saved candidate and called the existing pure `p0_page` renderer.

## Finding

The host omits mechanically available enclosing-class context from excerpts that
begin inside a class. This is concrete for test lines 1770–1800 and the helper
excerpt 780–815. Search's complete-function regions also have unqualified function
names, without their containing class or bases. These omissions make those
particular views less self-locating than the host can make them.

They do not explain all six responses. Test lines 900–1110 already contain the
relevant ordinary parser test-class header and bases. From C02 onward, lines
1–250 also contain `BasicTestCase(CfgParserTestCaseClass)` and the base's complete
configuration helpers. Existing file outlines provide the other class names,
bases and extents in two pages; Qwen did not request that operation in C01–C06.
An exact helper-name search could locate the remaining helper. No delivery failure
or source eviction was found in these inspected inputs.

This earns consideration of a small source-context presentation experiment, not
a conclusion that missing context caused every read or prevented completion.

## Evidence inspected

The audit directly inspected all six saved wire inputs, complete reasoning and
final replies, their actual results, the starting candidate and state, and the
host paths producing excerpts, outlines and search regions:

- `../run-002/calls/C01-wire-request.json` through `C06-wire-request.json`, with
  corresponding `*-assistant-reasoning.txt`, `*-assistant-content.txt`, and
  `*-host-result.json` files.
- `../run-002/starting-candidate.json` and `starting-state.json`, including
  historical operations 87–89. Historical custody does not imply current display.
- `src/working_set_exp/{working_session,feedback_session,operable_session,decision_session,hierarchical_p0,p0}.py`.

All six requests use ordinary presentation with
`selected_bodies_omitted=false`. The inspected candidate is
`047eeceb0bc5b21006965a5acec83b6f79e1ddcb4ea8744b30985d3c20c52f78`.
Its `Lib/test/test_configparser.py` has 2,210 lines and SHA-256
`33711931ae2059fd96323f6538986b1ca8d8aa0b7d9da5e3962e2d1fad3cb88d`.
Reconstruction from saved bytes reproduced the candidate identity. Locations
below refer to that exact file, not a later edited version.

## What the excerpts establish

| View delivered | Context present | Context absent or limited |
| --- | --- | --- |
| Test 1770–1800, C01–C06 | Exact method bodies, including `test_interpolationmissingoptionerror` at 1773–1785; the test visibly constructs the exception directly. | Containing class header and bases are outside the excerpt. It belongs to `ExceptionPicklingTestCase(unittest.TestCase)`, 1698–1918. Indentation and method names suggest a test class but do not establish its identity. |
| Test 900–1110, C01–C06 | `ConfigParserTestCase(BasicTestCase, unittest.TestCase)` at 909, its `config_class = configparser.ConfigParser`, existing interpolation tests and `get_error`/`get_interpolation_config` calls. Several later class headers, bases and policy overrides are also present. | The opening two lines belong to the end of `BasicTestCase`; the range ends inside a later method. The bodies of the two called helpers are elsewhere. This is not an excerpt uniformly lacking class context. |
| Test 1–50, C01 | Imports and `CfgParserTestCaseClass` at 36, including `interpolation = configparser._UNSET`; beginning of `newconfig` at 47. | Its constructor forwarding is cut at 50. `BasicTestCase` begins at 69 and is not yet present. |
| Test 1–250, C02–C06 | Complete `newconfig` 47–61 forwards `self.interpolation` and other settings to `self.config_class`; `fromstring` 63–66; `BasicTestCase(CfgParserTestCaseClass)` at 69. | `get_error` is at 584–591 and `get_interpolation_config` at 783–808. Reading 1–250 does not deliver them. |
| Test 780–815, C06 | Complete `get_interpolation_config` 783–808, with the comment “shared by subclasses”; start of a different helper at 810. | The parent `BasicTestCase` header is not in this excerpt. It is visible separately at 69, but the delivered source objects do not state its end at 901, so the parent-child relationship is not established by those headers alone. `get_error` remains absent. |

Qwen's C01 question about the class containing lines 1770–1800 is therefore
grounded in a real omission. Its C06 description of that source as “what appears
to be a pickle/serialization test class” remains appropriately uncertain. By
contrast, repeatedly seeking the general `BasicTestCase` inheritance relation
after C01 does not identify another missing header: the relation is already in
the exact source then displayed.

The test class for the Extended policy is named
`ConfigParserTestCaseExtendedInterpolation`, 1191–1359. There is no test class
declared as `class BasicInterpolation`. Policy-class names and test-class names
are different here. The C03 literal search's empty result is truthful; it is not
evidence that the host hid a matching class.

## Operations selected and resulting information

| Response | Final operation | What the inspected evidence supports |
| --- | --- | --- |
| C01 | Read 50–250 | Obtains the base helpers and `BasicTestCase` header. Does not obtain either named helper Qwen was seeking or the class containing 1773. |
| C02 | Account only | Records the acquisition plan; discussion says it will search, but no search executes in this response. This consumes a request without new source. |
| C03 | Search `class BasicInterpolation`, offset 0, limit 8 | Returns zero matches correctly. Its result is present in C04. |
| C04 | Search `Interpolation`, offset 0, limit 16 | Returns the first 16 of 96 matches and continuation offset 16. It locates the helper at 783 and existing interpolation test at 912, but this first page does not reach the Extended-policy test-class header. |
| C05 | Read 780–815 | Follows the actual returned helper location and obtains its complete body. This is source-directed acquisition, not an invented coordinate. |
| C06 | Read 250–500 | Qwen says it seeks `get_error` and interpolation test-class structure. The requested range contains neither `get_error` at 584–591 nor the Extended class at 1191. The read is accepted; its coordinates are exploratory, not evidence-derived locations for those targets. |

No C01–C06 reply requests a file outline, pages the generic search, searches the
exact `get_error` name, or retrieves a previous search result. This describes the
observed choices; it does not establish that those operations would have led to
completion or that every first read was unnecessary.

The C04 search result includes reusable complete-function regions for `newconfig`
47–61, `get_interpolation_config` 783–808 and `test_interpolation` 912–926. Each
region provides path, file identity, extent and address, but a bare `name`, not a
qualified name such as `BasicTestCase.get_interpolation_config`. The host already
parses the complete Python file to derive these extents; parent-class context is
mechanically available without semantic relevance judgment.

The previous `class ` search, archived as operation 88, returned only the first
16 of 46 literal matches with `next_offset=16`. It included the Basic and ordinary
ConfigParser headers, nested classes and `config_class =` assignments, but not
the Extended or pickling class headers. It was a literal search, not a complete
class inventory. C01 displays its recent-activity query, not that result body.

C06 correctly observes that results 93–94 are no longer in its current input.
Their query rows remain visible, and exact historical retrieval remains
available. Only C05 has the complete latest generic-search body. The selected
source excerpts themselves remain visible; source loss and nonretention of a
navigation result are separate facts. The model-authored account retains the
search plan rather than the discovered class/function relationships. This audit
does not establish whether persisting those search facts would change the next
decision.

## Existing, unused means of obtaining structure

The actual system reference describes `p0_page` as returning a scoped directory
or file-outline page with source locations. Its argument form is present. It does
not explicitly advertise that class rows include base expressions. The renderer
does provide them.

A pure read-only call to the current `p0_page` on the saved candidate returned:

- Offset 0: 24 of 31 top-level symbols, including `BasicTestCase` 69–901,
  `ConfigParserTestCase` 909–1004 and
  `ConfigParserTestCaseExtendedInterpolation` 1191–1359, with their signatures
  and bases. Its next offset is 24.
- Offset 24: seven symbols, including
  `ExceptionPicklingTestCase(unittest.TestCase)` 1698–1918; no further page.

This was an audit-side rendering, not information delivered to Qwen or a native
token-admission trial. The operating wrapper also provides reusable source-region
addresses for those outline entries. An outline address is not source evidence
authorizing an edit. The outline only lists top-level symbols; it does not list
`get_error` as a method. Existing literal search can locate that exact name and
return its complete function extent without reading the intervening file.

Thus the host exposes the needed class structure through an available operation,
while ordinary excerpt and function-region presentation omit some of it. Both
facts matter. “The information exists in a tool” does not make every displayed
excerpt self-explanatory; “the excerpt lacks its parent” does not make the
information inaccessible.

## Potential narrow remedy and evaluation boundary

If a prospective change is selected after this run, the narrow candidate is a
mechanical source-context annotation: enclosing symbol's qualified name,
declaration signature or base expressions, and exact declaration/scope
coordinates, bound to the displayed file version. Apply it to an excerpt or
function region that otherwise lacks its container. Do not automatically acquire
the entire class, infer inherited behavior, invent method resolution, or turn
navigation metadata into edit eligibility. Any explicitly delivered signature
bytes and mere addresses should retain their distinct roles.

An even smaller discoverability change would say that the existing file outline
contains top-level class signatures, bases and extents. Neither alternative is
proven useful by this audit. Do not implement both and attribute an effect to one.
First check whether an existing outline request already answers the actual
structural uncertainty; this avoids creating a new operation for an existing
capability.

Engineering qualification should cover an excerpt beginning inside a method,
multiple classes in one range, nested/decorated definitions, aliases or dynamic
bases, parse failure, changed source coordinates, exact source identity and
capacity cost. A mechanically reported base expression does not certify the
runtime inheritance semantics. The actual next input must contain the context
claimed, with unchanged source and edit guards.

The behavioral question is whether Qwen uses the context to locate the needed
helper or choose an appropriate insertion point, then saves and checks a useful
contribution. Compare the same exposed state and actual information costs; do not
supply the evaluator's desired insertion coordinates or draft. Retain a no-change
outcome if the context does not improve the decision. Count broad reading,
repeated searches, saved correctness and complete-loop cost separately.

A changed presentation may reduce structural uncertainty while leaving unrelated
deliberation or acquisition unchanged. This six-response audit cannot assign the
whole trajectory to one omitted annotation, establish the necessity of a complete
file inspection, or predict the run's eventual outcome.
