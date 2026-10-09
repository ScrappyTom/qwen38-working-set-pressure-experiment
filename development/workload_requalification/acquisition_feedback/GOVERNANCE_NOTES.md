# Acquisition qualification notes

- Qualification002 passed and its six admitted transitions replay exactly from
  saved native measurements. See RESULTS.md and review/VERIFICATION-002.json.
  Combined CPUqualification is43checks after adding the5continuation cases.
- Reconcile three extents explicitly: the requested range, the delivered page,
  and today's selected source view. Joining or refreshing selected source does
  not change what a historical acquisition returned.
- Attribute a shortened page to the actual sizing policy. A preferred feedback
  margin is not proof that the hard physical/admission ceiling forbids more.
- Budget feasibility must include plausible acquisition paths, not only a
  researcher-selected shortest route. The prior24-request limit really left
  insufficient time after broad reading; the declared continuation cannot be
  reported as completion inside that original opportunity.

- The closed E18 result/plan was published as4ecf3162 before host changes.
-38focused CPUchecks pass, including8new acquisition cases,3binding cases,
  7prior feedback repair cases and20DecisionSession cases. These cover the added
  facts before measurement, current/history extent separation, unseen group
  acquisition, edit authority after actual delivery, and separate/joint rejection
  outcomes. They are engineering checks, not Qwen outcomes.
- Native qualification001 preserved the real crowded C16–C19 transitions and
  their new measured inputs. It then failed in the researcher harness: the helper
  called _fits_feedback on a fresh session with no last receipt. The normal run
  path measures that initial input directly. This is a harness precondition error,
  not an observed actor failure or a reason to patch production feedback handling.
  Exact failed evidence and the executed qualifier source are preserved under
  qualification-001 and source_history/qualify-001.py.txt. Correct the helper to
  use feedback fallback only when the actual initial measurement exceeds the
  hard ceiling, then execute separately numbered qualification002.
- The ordinary-headroom and hard-ceiling-only diagnostics are engineering cases.
  Do not present the diagnostic as a changed production policy or a matched Qwen
  comparison. Native counts can shift paging because the new reports occupy space;
  any apparent improvement in page length is not a behavioral or efficiency result.
