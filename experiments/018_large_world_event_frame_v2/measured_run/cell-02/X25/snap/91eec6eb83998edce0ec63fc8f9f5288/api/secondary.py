from policy.current import active_prefix


def normalize_secondary(value: str) -> str:
    return active_prefix() + value.strip().upper()
