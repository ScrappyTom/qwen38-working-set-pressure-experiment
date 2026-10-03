# Evaluator-only audit corrections

The first post-seal audit invocation used `CHK-REVIEW-0001`, outside the existing
observation-reference grammar. ObservationStore rejected it before checker
execution. The reviewer script was corrected to use `CHK-0001` inside its own
separate postseal-check directory. No actor input, saved source, grade or host
contract was changed. This is an audit-script mistake, not a live host defect.

The first audit JSON also looked for an `accounts` snapshot field rather than
deriving the current account from the restored exact operation history. That
reviewer-only field was corrected using the actual restore API, without repeating
the checker or changing any observation. Account text remains the actor's text.
