from policies.current import active_policy_prefix


def normalize_name(value: str) -> str:
    return active_policy_prefix() + value.strip().casefold()
