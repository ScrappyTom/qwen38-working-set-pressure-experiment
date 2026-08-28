def delivery_key(name: str) -> str:
    return "nebula-" + name.strip().casefold()
