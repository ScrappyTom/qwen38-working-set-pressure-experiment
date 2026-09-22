# Host and saved artifact audit

## Custody and execution

`review/analyze.py` adapts the existing reference-repair exact verifier to
`repair_task.Task('artifact_map', '001', replay_folder)`. Its task-neutral artifact
measurement does not import parser-specific test-count metrics. It verifies the
response seal, its aggregate, source and local-runtime identities, full custody
chain, native request bytes/counts, complete response channels, decoded proposals,
every intermediate state and candidate, and normal closure. Observations are
replayed from stored bytes; no checker, tokenizer or model is invoked.

The first execution passes: 466 source identities, 458 custody records, 31 distinct
native inputs, 20 replies, 30 actual operations and one preserved observation.
All operations belong to this new run. Runtime closure is verified. Original run
bytes and source-bound files were not modified by review. `ANALYSIS_PROVENANCE.json`
identifies the helper and reused verifier. `ASSESSMENT.json` contains complete costs,
delivery identities and exact current-source checks.

Every nonterminal receipt reaches the next actual input (29 of 29). Source bodies
arrive in `working_set.sources` with feedback references rather than duplicate
content. Seventeen displayed extents were compared against their exact candidate
and file identity. Adjacent/overlapping unit-module reads merge to one complete
459-line source. After editing, all selected source bindings refresh to the actual
successor; unchanged sources retain their byte fingerprints. No forced source
omission, rejected action or capacity fallback occurs.

## Independent artifact assessment

The final candidate differs only in `src/addressable_information_layer/patching.py`:

```diff
-    new_map = address_map
+    new_map = build_address_map(new_artifact)
```

The original/current `apply_patch_preview`, `materialize_reopen`, map construction,
unit construction and exact extraction were inspected directly. The apply routine
constructs edited text and imports its successor artifact. Returning the old map
couples new text with old unit extents/content hashes. Rebuilding from the actual
successor yields ranges from its AST and hashes from the same text extraction
used by reopen. The map's version binding also follows that successor.

This is a correctness argument about the actual code, separate from the host's
acceptance. No extraction or stale-reference guard is weakened. The stale preview
hash check, old-reference resolution, content-hash comparison and actual source
replacement remain unchanged. The remaining 24 files are byte-identical. A later
accepted edit repeats the same rebuild from its own successor. An unchanged-content
operation rebuilds equivalent content-derived units rather than inventing changed
content.

The unchanged public checker was also read directly. Its eight assertions exercise
accepted initial application, independent exact extraction, current-function reopen,
unrelated-function reopen, rejection of the old exact reference, subsequent update,
subsequent reopen and unchanged-content reopen. Actual CHK-0029 exits zero with
complete capture: 695 stdout bytes, no stderr. Its printed record additionally
reports the returned map matching the updated version. These are concrete
behavioral obligations, not eight independent investigations. The checker retains
its historical construction-probe docstring; the new package prospectively freezes
its unchanged bytes as the selected public acceptance procedure.

No new test or documentation artifact is required for this original source-repair
task. Added-test counts are inapplicable. No further independent execution was
needed to assess this one-line repair after exact replay and source review.

## Actual decision-input limitations

`NAVIGATION_INFORMATION_PATH.json` records C04–C13 input identities and navigation
fields. A six-row recent action list retains paths, offsets and handles but loses
tree results' entry paths, limits and completion counts. The root description stays
unchanged. The previous page body leaves on the next operation despite the C04–C07
inputs using only 5,103–5,457 tokens. The maximum tree page size is 16 entries for a
25-entry directory. Retaining the archive does not provide a combined visible map.
The original run is not altered to repair that omission.

`CHANGE_INFORMATION_PATH.json` exhaustively checks C19 input fields. The exact old
line, old fragment and diff are absent; new source is present. The archived public
patch matches the complete final reply, and `diffs/EVT-0027.patch` remains exact.
The latest feedback exposes location and before/after bindings, while the current
account still reflects the question from before the source acquisition. C19's
reconstruction occurs with truthful but incomplete change explanation. A current
public check remains an available useful next operation and is eventually selected.

These findings are not assigned a causal fraction of the total cost. Some repeated
navigation occurs while actionable paths or an outline are visible. Qwen explicitly
recognizes the incident's earlier episode in C19. The record does not establish
renewed incident confusion, a failure of account storage, or missing source delivery.
It establishes successful work with avoidable-looking information turnover that
warrants separately measured host presentation qualification.
