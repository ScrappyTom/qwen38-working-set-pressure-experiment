CERT_GROUPS = ("north", "south", "east", "policy")


def certified_count() -> int:
    return len(CERT_GROUPS)
