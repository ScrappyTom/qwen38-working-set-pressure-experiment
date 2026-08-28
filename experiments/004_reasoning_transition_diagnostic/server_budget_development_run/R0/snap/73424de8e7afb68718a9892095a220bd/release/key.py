from policy.namespace import active_namespace

def release_key(name: str) -> str:
    return f"{active_namespace()}{name.strip().casefold()}"
