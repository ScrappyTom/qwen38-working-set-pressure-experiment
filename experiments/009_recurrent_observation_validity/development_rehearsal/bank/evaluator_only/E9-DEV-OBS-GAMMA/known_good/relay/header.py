def relay_header(name: str) -> str:
    return "T2##" + name.strip().casefold()
