"""Opt-in report projection; stored observations and historical receipts stay exact."""
from . import coherent_diagnostics
from .recovery_context_session import RecoveryContextSession


class CoherentDiagnosticSession(RecoveryContextSession):
    assessment_api = coherent_diagnostics
