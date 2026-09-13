# Executed review validation

No new model request and no production host change occurred during review.
The full host suite was not rerun. Preparation's 15 focused tests remain its
historical result, not additional tests executed by this review.

- `verify_configparser_execution.py` verifies the response seal and custody,
  194 frozen sources, all 65 attempted native inputs, all 32 exact raw/extracted
  responses and all 32 actions/results/candidates/sessions/snapshots. Replaying
  the actual C30 check also reruns the frozen upstream, independent contract
  and unchanged candidate test module, reproducing the exact overall failure.
  The final pass is preserved as VERIFICATION_FINAL.json; it additionally
  verifies every terminal prefix, the first fitting input's withheld result,
  the explicit denial record and the absence of a C33 model request.
- `probe_configparser_patch_boundary.py` compares the explicit C11 proposed JSON
  and final JSON, then compiles and executes saved library copies after C10–C13.
  The two damaged copies compile but fail with missing `_UNSET`; before/after
  copies execute. This is post-run engineering evidence, not a new actor score.
- `report_configparser_execution.py --output ...` derives the complete 32-turn
  metrics and terminal admission table in MEASUREMENTS.json from saved custody.
- `probe_configparser_recovery.py --output ...` exercises all 32 saved result
  wrappers and four patch payloads through the actual executor. All bytes and
  hashes match; maximum wrapper is 21,229 bytes and the candidate is unchanged.

Run these with Python 3.12, UTF-8, `PYTHONPATH=src`. Output destinations are fresh
files; do not overwrite sealed evidence or a previously claimed validation.
The verifier and probes have no inference path. The frozen 194 source bindings
are checked as recorded rather than regenerated from the expanded scripts folder.

Preserved review mistakes:

- The initial metrics invocation piped `Tee-Object` into `Select-Object -First
  134`. PowerShell stopped the upstream pipeline after that prefix, leaving an
  incomplete derived JSON file. A direct parse failed at line 135. The bytes are
  preserved as MEASUREMENTS_INCOMPLETE_ATTEMPT001.txt. The helper now writes its
  complete output directly to a fresh file before printing a short receipt;
  the final MEASUREMENTS.json parses and contains C01–C32.
- The first recovery probe omitted `probe_id` and `probe_body` when constructing
  ToolExecutor, causing TypeError before executing a retrieval or writing a
  result. The probe supplies explicit None values; production code is unchanged.
  The executed successful probe is RECOVERY_PROBE.json.

Neither mistake changes the recorded Qwen trajectory. Direct transcript and
artifact review is documented separately from these mechanical checks.
