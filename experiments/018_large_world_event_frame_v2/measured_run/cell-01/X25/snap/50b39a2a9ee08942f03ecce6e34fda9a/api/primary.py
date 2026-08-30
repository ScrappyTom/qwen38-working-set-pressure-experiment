from policy.current import active_prefix


def normalize_primary(value: str) -> str:
    return active_prefix() + value.strip().casefold()
