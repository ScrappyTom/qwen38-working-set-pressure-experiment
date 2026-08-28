AUDIT_GROUPS = ("alpha", "bravo", "policy")


def audited_count() -> int:
    return len(AUDIT_GROUPS)
