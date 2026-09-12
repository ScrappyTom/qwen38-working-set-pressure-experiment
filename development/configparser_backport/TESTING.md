# Executed preparation checks

The exact commands and results are preserved in the attempt logs in this directory.
Python 3.12.10 is used with `PYTHONPATH=src`; no model completion endpoint is used.

- `qualify_checks.py`: the original tagged upstream suite runs 355 tests with
  five skips; the newly requested behavior fails before repair.
- `qualify_reference.py`, attempt 002: reference contribution passes; six negative
  controls fail for their intended omissions/incorrect behavior. Seven actual
  check results reopen exactly. The first failed qualification and its original
  source are retained.
- `prepare_configparser_inputs.py`, absolute-path attempt 003: 118 native counts,
  23/33/24 schema-valid operations, three correct submissions, every immediate
  result available in the following prepared input, peak input 23,782. The earlier
  schema-oversized and unsealed preparations remain separate development evidence.
- `python -m unittest discover -s tests -p test_configparser_execution.py -v`:
  focused new runner tests, including actual checked tools and exact prepared
  native inputs. The original failed assertion is preserved in attempt 001 and
  `revisions/test_configparser_execution_attempt_001.py`; the final result is in
  `execution-tests-attempt-002.log`: all 15 tests pass in 16.972 seconds.

The execution tests use mocked model responses. Their complete-loop case
reconstructs all 23 selected native inputs, executes the actual tools and compares
all resulting action/result pairs with the qualification. They do not benchmark
Qwen. Smaller guard tests intentionally use mock counts to isolate control flow;
their counts are not capacity measurements. The failed-attempt lifecycle test
uses a mock owned runtime, verifies the seal, and rejects a second attempt.

No full host-suite rerun is claimed: there is no new shared-host implementation
change in this tranche. The task checker independently runs its real upstream
regressions and explicit behavioral contract. Its documentation-marker check
does not establish prose accuracy, and test-count differences do not establish
that existing test definitions were preserved. Both require direct final-artifact
review after live work.
