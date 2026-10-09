# Run001 closed by owner; no further GPU work

Latest owner instruction changed to immediate shutdown. The verified owned GPU
server was stopped at 2026-10-09 15:29 Denver time. The runner saved its partial
state, closed its port and sealed the stop. Both processes are absent; GPU memory
is released. The heartbeat finish-qwen-run-and-review is PAUSED.

All completed C01-C17 inputs/full replies/effects and C18's input were reviewed.
C18 returned no content and is not available for interpretation. Exact replay and
CPU artifact assessment are complete. Read RUN001-RESULTS.md and 001/CLOSURE.json.
The current candidate remains the one listed below; no reviewer patch was applied.
Do not resume, retry, start a successor or follow the older execution instructions.

The following monitoring handoff is historical, superseded by this closure.

## Historical monitoring handoff

The owner's latest instruction is: "Once it finishes, let's go ahead and stop the
gpu, have you review and summarize for me." This supersedes the older top-level
continue-until-blocked instruction. Do not launch another model run, successor,
retry, extension, consultation, tokenizer qualification or GPU experiment.

## Current process and review position

- Repository: C:/Users/danmc/Isolated experiments 8.24.2026/qwen38-working-set-pressure-experiment
- Published frozen revision: 9cf856db, main.
- Active unified exec session: 26576.
- Command: python -B development/workload_requalification/configparser_unnamed/run_unnamed.py run --version 001
- Owned llama-server PID: 31392. Do not kill other projects' processes.
- Temporary ten-minute thread heartbeat: finish-qwen-run-and-review. Pause this
  automation after the completed review; retain its other fields when updating.
- Last completed reply: C17. C18 was generating at the last inspection around
  2026-10-09 15:08 local; server progress was advancing. Long generation is not
  evidence of a stalled server. Poll the existing process; never rerun the command.
- Direct review is complete through all of C17 (79,464 reasoning characters), its
  final/effect and the actual C18 input. Notes: RUN001-READING_NOTES.md.
- C17 reread lines 1290-1360 without editing; current candidate remains:
  75d37916ddbf52db8ebfd559778c804c8dde3f4728931b7dff8e6e006b65fb03.
- Eight library edits, 28 actual operations after C17. No test/documentation edit,
  public check, rejection or submission yet. Feature still incomplete then.

The run allows 40 requests/120 operations, medium uncapped reasoning, one primary
operation plus optional account. Keep all bound host/task/checker sources frozen.
Do not coach, extract unfinished drafts, change selection, alter budgets or edit
the candidate. Reviewer files are separate and may be updated.

## Continue direct review

Read every newly completed input, complete reasoning/final, actual effect and next
input. Use review/read_call.py with N and --part input|reasoning|final|effect.
For reasoning use successive --start/--end slices (about 26,000 characters), and
check the printed total to cover the whole response. The input helper compares
actual stored packets and gives exact deltas for previously inspected source;
it does not change evidence. Read newly supplied source in full.

Current observations are provisional and documented in the notes. Full current
library source has stayed visible since C08. Many replies re-plan the whole feature
before saving a small edit, while accounts largely preserve checklists rather than
the repeatedly rediscovered first-option parsing distinction. One operation per
reply is a real interface constraint, but a single larger contiguous replacement
is permitted; the host does not require one-line edits. Do not attribute all cost
to that constraint or equate private plans with saved work.

The actual server launch reports all 66/66 layers offloaded, CUDA0 model buffer
9,685.21 MiB and CPU-mapped buffer 397.85 MiB. Large system RAM use alone does not
establish CPU layers or spill. No runtime setting was changed.

## Closure order

1. Let this one bounded attempt close normally. The runner uses owned_runtime and
   closes its server before producing RESPONSE_SEAL.json. If a genuine new blocker
   appears, preserve it and report it; do not silently restart or rescue the run.
2. Verify the actual owned process has ended, the runtime's recorded port is free,
   and GPU memory is released. If cleanup failed, stop only the still-owned server
   after verifying its command/ownership. Do not reset the GPU or terminate other
   apps. User means release this run's GPU workload, not disable the device.
3. CPU-only exact replay:
   python -B development/workload_requalification/configparser_unnamed/review/verify_run.py --version 001
4. CPU-only independent assessment:
   python -B development/workload_requalification/configparser_unnamed/review/assess.py --version 001
5. Directly inspect saved implementation, new tests/assertions and documentation;
   execute new examples under the intended ordinary namespace with this candidate.
   Existing private checks do not replace direct review. Preserve real failures.
6. review/check_sensitivity.py is qualified on the evaluator reference, not yet on
   the actor artifact. It expects a passing final control. Do not falsely run or
   report it as actor coverage if the run stopped incomplete. Two faults cover
   header suppression and sentinel identity, while preserving the older tests.
7. review/export_work.py currently requires a verified submitted final candidate.
   If incomplete, do not present a partial artifact as complete; adapt a separate
   clearly labelled partial export only if useful.
8. Write a detailed results report and a self-contained user summary: actual
   outcome, preserved work, correctness/coverage, costs, direct observations,
   apparatus limits, host/process lessons and GPU-off confirmation. Include failed
   final requests in cost where measured. Never infer missing duration/usage.
9. Update operative AGENTS.md/STATUS.md to this closed result and owner-requested
   stop. Commit and push authorized reviewer/evidence changes. Never stage private-
   runtime, model weights or __pycache__. Preserve exact workload bytes (-text).
10. Pause the temporary follow-up automation after review/report is complete. Do
    not start the next workload. Leave a recommendation for the owner to consider.

Known uncommitted reviewer work: read_call.py, RUN001-READING_NOTES.md,
check_sensitivity.py, SENSITIVITY-TOOL-QUALIFICATION.json and this handoff; run-001
is newly generated evidence. Do not mistake these for actor artifacts.
