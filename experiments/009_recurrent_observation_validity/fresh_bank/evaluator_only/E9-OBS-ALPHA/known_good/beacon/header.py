def beacon_header(name: str) -> str:
    return "N9%%" + name.strip().casefold()
