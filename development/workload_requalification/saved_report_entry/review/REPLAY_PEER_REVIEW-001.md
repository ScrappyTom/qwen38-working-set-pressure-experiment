# Saved-report replay peer review

Reviewed the phase-aware `verify_run.py` before any closed saved-report model run existed. The reviewed helper SHA-256 is `993656862a0e5c623c1b6fdf1b9bbaec8fddfec1665904d39756f2abf65fea64`. This helper and this note are outside the frozen Task source closure. This is a source review, not a successful replay result.

I directly read the helper, live `PhaseLoop`/common invocation and snapshot code, saved-report setup/transition/restore implementation, capture presentation auditor, and observation execution/replay boundary. I also inspected the existing preparation's first actual endpoint, apply-template, tokenize, and native-input artifacts to check the request relationships. I did not execute a checker, model completion, tokenizer, native runtime, or closed-run verification.

No remaining blocker was found for the declared completed journey, normal operator stop, incomplete or malformed final, and recorded ValueError setup/processing stops. The live runner prepares the request before consuming its decision slot; replay constructs those same bytes, marks actual presentation, consumes the same slot, and only then processes the saved public reply. Cumulative identifiers and phase counters are never reset. Phase-two setup is conditional on the actual executed check after an accepted report edit; source eligibility and selected material are cleared by the same transition function, while the authored account and archive remain.

Replay compares every setup acquisition, ordinary operation, state/candidate/preceding-feedback checkpoint, and saved diff. It connects the run manifest to the unchanged preparation and source closure, validates custody hashes, and looks up admission by the exact request hash. Actual capture bytes and original historical bindings are checked separately from visibility flags. The inherited three flat receipts remain historical and are not recreated as new observations.

Three gaps found during review were corrected in the helper:

- Malformed message text or cache/timing shapes are classified as inert terminal input only for a stopped attempt with no selected reply, host result, or operation artifacts. They are not executed or taken from private thinking.
- A stopped partial assisted setup now matches the actual stop type/message and partial acquisition snapshots, without requiring or inventing a completed setup snapshot. Started and completed phases are reported separately.
- The saved apply-template request must equal the endpoint request, and the saved tokenize request must contain that exact native text with `add_special=False`. This closes a request-evidence gap without new tokenization.

The initial session uses `ObservationStore(replay=True)`. Its check path returns a saved outcome only after checking candidate, checker definition, scope, and operation handle; it returns before the subprocess branch. The helper additionally blocks `subprocess.Popen` during replay. Missing observations or unknown admission inputs fail verification rather than rerunning execution.

Mechanical replay cannot establish that Qwen interpreted an account or capture correctly, that an authored report is substantively right, or that the declared assistance was unnecessary. Those require direct transcript and artifact review after closure. Unexpected runtime/storage failures remain fail-closed rather than being silently accepted as one of the recognized terminal paths. A real closed attempt is still required to qualify the helper end to end.
