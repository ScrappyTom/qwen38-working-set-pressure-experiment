# Repair the response boundary, then rerun the same task

Owner direction: "Complete the repairs and then rerun."

The previous attempt remains closed at 2bfaa2f4. Its first response demonstrates
a host defect: a final-only user grammar starts inside the native open thinking
block, blocks its close delimiter and allows end of generation without final content.

Implement an opt-in transport envelope around the unchanged final-reply grammar.
It must allow thinking, require the pinned thinking-close delimiter, and then
constrain the ordinary JSON or literal SOURCE final reply. Verify the exact native
generation suffix before using this envelope. Preserve separate reasoning/final
fields, enabled medium uncapped thinking, complete-final execution and all task
guards. Do not change the model, prompt reference, task, checker or source selection.

First qualify vocabulary/sampler paths across the delimiter, including misleading
action-shaped reasoning, incomplete final output, literal backslashes/newlines and
invalid final syntax. Then make two small, separately recorded endpoint smoke calls
(ordinary JSON and literal source) using the corrected grammar and the same pinned
runtime. These calls exercise transport only; they receive no task evidence and
execute no task actions. Save their complete inputs, reasoning, finals and costs.

Once these checks pass, render/tokenize the same original task start. Assert that
the old and repaired initial requests differ only in grammar and that the native
input bytes are identical. Publish the repair, qualification and frozen task package
before dispatch. The present owner direction authorizes the smoke calls and this
single separate rerun; do not ask again.

The task rerun has sixteen requests and forty-eight operations, seed 961221,
Qwen3.8-27B UD-IQ3_XXS, q4 K/V, no MTP, 56,576 physical context, 23,808 input ceiling,
and medium uncapped thinking. Start at the original operable-recovery checkpoint,
with no supplied account, compact group, repair or check. Existing memory monitoring
and advisory threshold remain. No coaching, private-draft execution, retry or change
inside the attempt. Preserve and close any failure before further development.

Review the complete actual inputs/outputs and resulting work. Separate transport
repair, host feedback, task correctness, useful progress, termination and cost.
Update the running notes and governance, verify custody, commit and push results.
