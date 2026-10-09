# Remaining-entry inspection during MINT001

Evaluator planning only; no active-run or bound-source changes. Complete MINT and
the separately prepared SABLE entry before selecting the next implementation.

INVENTORY.json still lists original entries rather than a closed corpus. Direct
inspection confirms that sharing a phase label is insufficient for adapter reuse:

- E2-OBSERVATION asks for its wire probe before a progress edit. Its fixture stores
  one probe body and required_full_reads rather than the E14 per-phase dictionary.
  MINT's requirement for a post-edit current probe at fork cannot be copied into
  that older task without changing its contract.
- E12-SOURCE-ORBIT has four phases. Phase C changes the governing policy to zenith-
  while preserving Phase B's earlier name behavior. Phase D must reacquire that
  new policy and use it for a separate footer. A final source pass alone does not
  establish that temporal relationship.
- E12-OBS-COMPASS also has four phases. It produces compatibility observations at
  successive candidates and requires the right exact result for label, header,
  and footer. Older exact observations stay available but become stale.
- The current phase_session.Session explicitly admits exactly A/B, derives B from
  any accepted fork, and accepts only one phase boundary. It is a qualified adapter
  for the entries executed so far, not a general implementation of those recurrent
  contracts. Do not label their final files as requalified through this adapter.

Next mapping must bind the exact original task, fixture, sources, check definitions,
probe timing and actual exposed entry before deduplication. Current original E18
missed recovery remains a temporal failure. Repeating a closed MINT/ANCHOR job or
counting duplicate task copies cannot close that failure or the recurrent entries.

Inspected source paths: experiments/002_single_boundary_reconstruction/fresh_bank/
execution_only/E2-OBSERVATION/FIXTURE.json; experiments/012_large_world_recurrent_continuity/
fresh_bank/model_visible/{E12-SOURCE-ORBIT,E12-OBS-COMPASS}/TASK.txt; the ORBIT fixture;
and phase_entries/phase_session.py. This note identifies differences, not a new
live-run approval package or evidence that the unimplemented transitions work.
