# Host responsibility after the operable recovery run

Owner direction: document the preceding host-focused assessment, plan and fix all
seven issues, and keep running notes usable for project governance. This assessment
starts from the actual C03/C04/C05/C06/C12/C13 inputs, saved output and checker
implementation at 5cca6668. It does not attribute the failure primarily to the actor.

1. The failed check reports ordinary success, six/seven detected faults and
   `primary_real_failure: null`, without naming the failed criterion. Raw mutation
   `successful=true` means a missed fault; `successful=false` means detection.
   `missing_paths` and `complete=false` under mutations look like obligations although
   the checker does not require those paths. The host must explain its assessment.
2. Diagnostic inspection returns 4,096 bytes ending inside serialized JSON. Capture
   completeness and page completeness are different but not clearly presented.
   Exact archival bytes should underlie coherent, scoped diagnostic records.
3. Recovery cuts a 725-byte account to 512 bytes despite a 5,761-token input and
   23,808-token ceiling. Instructions also say accounts are not truncated. Preserve
   exact storage and distinguish display reduction, using it only when needed.
4. Recovery reads are temporary, while ordinary reads accumulate. Reading test imports
   removes the preceding implementation inspection by policy, without a new capacity
   obstacle. Reading must have a consistent retention contract and explicit capacity
   fallback; retention must not require reconstructing hidden presentation mechanics.
5. `working_set.sources` can be empty with visible source in feedback, or empty with
   hidden designations in recovery. Present source bodies in one stable location and
   explicitly inventory actual visibility independently of custody/deduplication.
6. `current_check=null` means no public check although current tests failed elsewhere.
   Once diagnostic inspection replaces latest feedback, the failure reason is no
   longer a stable decision object. Unify scope-specific verification, applicability,
   failed criteria and submission eligibility without endorsing semantic accounts.
7. Edits require repeating exact old source and serializing new multiline code inside
   JSON. The transcripts show repeated escaping and indentation work. Preserve exact
   source/version guards while letting the host resolve an observed region and perform
   transport serialization of literal replacement text.

The process error was treating preserved, accurately labelled, delivered information
as sufficient evidence of interface adequacy. Qualification must also establish that
the input explains what happened, which criterion actually failed, and what remains
available for the next operation. These observed burdens do not identify a single
cause of all elapsed time, or prove that one presentation will ensure completion.
