"""Opt-in check scope for successive contributions with different contracts."""
from .jsonutil import sha256_bytes
from .working_session import WorkingSession


class ContributionSession(WorkingSession):
    def check_state(self):
        checked = super().check_state()
        if checked is None:
            return None
        sequence = int(checked["handle"].split("-", 1)[1])
        result = self.pairs[sequence - 1]["result"]
        matches = result.get("check_definition_sha256") == sha256_bytes(self.checker)
        return {**checked, "candidate_matches": checked["applies_to_current"],
                "check_definition_matches": matches,
                "applies_to_current": checked["applies_to_current"] and matches}

    def _ordinary(self, action):
        result = super()._ordinary(action)
        if action["action"] == "check" and result.get("accepted"):
            result = {**result, "check_definition_sha256": sha256_bytes(self.checker)}
        return result
