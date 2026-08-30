# Experiment 020 Apparatus Finding

## Disposition

Experiment 020 is mechanically valid, complete, and scorable.

The exact authorized run executed once, sealed all model responses before
evaluator access, replayed every shared and branch segment, graded every
terminal candidate after the seal, and shut down its owned server. No host,
transport, parser, checker, custody, candidate-binding, capacity, or runtime
accounting defect affected an outcome.

The response seal is
`97e32a24fbeeb7c867f977e460e00daaf1d7e25bad33ead2f81f44c6c28a9076`.

## Frozen identities

- bank:
  `E20BANK-03afc79d00c47ead26296a230a935869e1dc24605d70b764bc4adecd2cd95369`;
- execution package:
  `E20PKG-0d8e4a2c69fd0866526ec67fed21834b8498ea28ec46ad5702fe4848bae6be1c`;
- executable closure:
  `92b9c15965396bf98b74d8bdc44f518bd7fab1b0e29993d26ffb34fea73c78b3`;
- actor:
  `Qwen3.8-27B-AD-IQ2_S.gguf` at
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`;
- authorization record:
  `7f48dc46907dc8c66232a096cfb8cfcf2dbe467bcfa81954919ead58bf341fd5`.

The live preflight verified the authorization, bank, package, runtime, actor,
output-root absence, dedicated port, and executable closure. The closure was
verified again immediately before server launch.

## Execution integrity

The sealed run records:

- 106 prepared invocations;
- 106 actual HTTP completions;
- zero retry, repair, rescue, or capacity stop;
- one ordinary actor action rejected mechanically as an exact no-op patch;
- 105 accepted ordinary actions after that one bounded rejection;
- zero malformed endpoint envelopes or parser failures;
- zero runtime/offline token-accounting delta on all 106 completions;
- one unique endpoint response ID per completion;
- 1,625 files in the response seal;
- 12 independently replayed run segments;
- evaluator truth absent until after the response seal;
- exact server exit and port release.

The one rejected action occurred in cell 02 R50. Qwen attempted a replacement
whose old and new text were identical. The host returned the frozen
`tool_rejected` result. Qwen saw that result, explicitly recognized that no
change had occurred, reread current source, repaired it, passed both checkers,
and submitted. This is valid model behavior under the qualified host, not an
apparatus failure.

## Task compliance and grading

Every branch completed its prospectively required inspection before the first
accepted mutation:

- source family: all 11 frozen owner-source paths read exactly to EOF;
- observation family: current observation selected/reopened and all 10 frozen
  owner-source paths read exactly to EOF.

All eight terminal candidates:

- passed the model-visible `public` check on the submitted candidate;
- passed the post-seal hidden grader;
- were submitted with exact candidate binding.

No tests or evaluator files were model-visible. The saved hidden rows were
recomputed from terminal candidate custody during analysis and matched.

## Capacity and authentic pressure

The paired branches were byte-identical through their shared authentic 25k
boundary. R50 then retained all exact payload bodies under the physical
50,176-token slot. X25 mechanically externalized oldest exact bodies while
retaining the same readable event signal and a 1,000-token operating reserve.

| Cell | Family | R50 peak prompt | X25 peak prompt | X25 minimum adjusted headroom |
|---:|---|---:|---:|---:|
| 1 | source | 35,335 | 20,821 | 1,167 |
| 2 | source | 31,824 | 20,544 | 1,444 |
| 3 | observation | 27,933 | 20,940 | 1,048 |
| 4 | observation | 27,908 | 20,864 | 1,124 |

Every X25 request therefore remained inside the 25,000-token total envelope
after the 512-token runtime allowance and 2,500-token output reserve. Every
R50 request remained inside the physical slot. Unlike Experiment 018, R50 did
not physically stop; Experiment 020 is a quality/reliability and economics
comparison under authentic externalization, not another capability crossover.

## Canonical payload identity

The Experiment 018 result-of-result handle defect did not recur.

An explicit reopen created a new access event but retained the original
canonical source handle and provenance. X25 used `reopen_result` three times
and branch-local `reopen_observation` twice. Direct request inspection showed
that later event frames continued to identify the original canonical payload;
no nested source object or competing address was created.

This establishes the intended mechanical correction. It does not establish
that Qwen will avoid reopening already sufficient evidence; that remains actor
behavior and was directly observed in several X25 paths.

## Host-path conclusion

The host offered every frozen action, preserved every request and result, and
did not rescue or semantically steer a trajectory. The public and hidden
checks agree in all eight branches. Capacity admission, action budgets,
candidate bindings, observation bindings, and exact reopen provenance all
behaved as specified.

Experiment 020 therefore supports behavioral interpretation of all eight
branches. Its limitations are study scope, not invalid apparatus:

- two task families from one owner-controlled Python package;
- two seeds;
- explicit pre-mutation audit sets;
- one actor, quantization, reasoning budget, and tool surface;
- no R50 physical exhaustion in this run.

## Post-seal qualification

Post-seal analysis reran bank, package, closure, response-seal, all-segment
replay, exact endpoint/action/reasoning equality, and hidden-grade checks. The
analysis outputs reproduced byte-for-byte on a second run:

- `MECHANICAL_RESULTS.json`:
  `504bd01b71fe6e10d540b085642e62d6b12ed62c065b3a26429b3ca88ac363b2`;
- `TRANSCRIPT_INDEX.json`:
  `f9a06396c392130e01029a4e390bc21b5e53531b66b05d0d575d25bf222355fd`.

The relevant controller, event-frame, ecological, and canonical-payload test
set passed 34 tests. One pre-live test asserting absence of an authorization
record was intentionally deselected because the exact authorization is now
present and consumed; no execution or behavioral test was excluded.
