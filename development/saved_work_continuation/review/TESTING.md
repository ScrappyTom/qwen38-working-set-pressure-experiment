# Closed-run verification and offline qualification

No model rerun and no full repository suite were performed for this review.
The pre-exposure preparation's fourteen selected tests remain its separate
reported result. All checks below execute after the live runtime closes; the
three prepared probe sources also received a syntax-only parse before execution.

`verify_run.py` passes on its first execution. It independently verifies the
seal, hash chain, private runtime identity/lifecycle, 77 source bindings, exact
template/native input, all 14 tokenizer counts, consecutive prefix admission,
all raw output fields/actions/results and all 21 operations including setup.
It verifies candidate/session/payload snapshots and newest-feedback delivery.
Results: VERIFICATION.json and verification-attempt-001.log.

`assess_artifacts.py` passes on its first execution. It safely reconstructs the
captured AST constructor data, derives changed functions and first changed
expression from actual trees, and compares the saved final report. It separately
identifies C01's actual JSON failure and assesses its facts with one explicitly
diagnostic brace insertion; the saved artifact is never changed. It confirms
that C05's candidate is unchanged through submission, that all nonreport files
retain the starting repair, and that C09's disputed BUILD-A subtree is actually
resident and includes unary minus. Results: ARTIFACT_ASSESSMENT.json and
artifact-assessment-attempt-001.log. This is artifact evidence, not a model run.

`qualify_group_capacity.py` passes on its first execution, preserving eight
native counts: the two actual dispatched inputs and six selected-residency
counterfactuals. Both full report groups exceed the gate. No model input or live
retention policy is changed. Results and their seal are under
../group-capacity-001/; group-capacity-attempt-001.log preserves command output.

`development/long_work/qualify_large_files.py` passes on its first execution.
Its 116 actual isolated operations qualify 56 complete source pages and exact
historical retrieval, an accepted large-file edit, rejected stale edit, current
syntax check and exact predecessor recovery. It restores the module's process-
local admission constant and verifies tracked admission source is unchanged.
The tested 1 MiB cap is a counterfactual; actual tested files reach 47,907 bytes.
It does not prove all files up to 1 MiB work, admit long lines, establish model
delivery or validate application semantics. Results and seal are under
../../long_work/large-file-qualification-001/.

The probe sources and exact outputs are preserved for reproduction. Native
tokenizer/model runtime paths stay local. The sealed run is never rewritten to
include corrected metrics, alternative states or reviewer diagnostic edits.
