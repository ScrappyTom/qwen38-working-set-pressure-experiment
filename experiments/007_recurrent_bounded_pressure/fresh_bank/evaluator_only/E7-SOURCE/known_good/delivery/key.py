def delivery_key(name: str) -> str:
    return "quartz-" + name.strip().casefold()
