# Running implementation notes

First qualification: five selected CPU checks pass. Native actual-state trials
restore all six recent rows at C52:14772->15306 tokens and C48:15593->16199 tokens,
with every other input field unchanged. The actual recorded C48 check/C49 submission
replay with unchanged outcomes, no new execution or inference. This is information
availability evidence, not proof that Qwen would act differently.

Before release, code review identifies an additional composition concern: calling
the full polymorphic _fits for optional rows lets NavigationMixin try dropping
previously fitting navigation/change details first. These two roomy native states
do not exercise that tradeoff. Preserve qualification001 and its source; add a
successor admission override that measures rows on the already-admitted arrangement,
without invoking its optional-content fallback again. Test that priority explicitly
and repeat the native boundary qualification for the successor.
