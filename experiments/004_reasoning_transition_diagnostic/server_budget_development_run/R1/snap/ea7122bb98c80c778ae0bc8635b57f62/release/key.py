from policy.namespace import ACTIVE_NAMESPACE


def release_key(name: str) -> str:
    return ACTIVE_NAMESPACE + name.strip().casefold()
