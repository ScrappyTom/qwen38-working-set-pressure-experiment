AUDIT_GROUPS = ("cedar", "maple", "oak", "channel")


def audited_count() -> int:
    return len(AUDIT_GROUPS)
