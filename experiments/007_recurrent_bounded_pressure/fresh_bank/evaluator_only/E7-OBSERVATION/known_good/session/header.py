def session_header(name: str) -> str:
    return "M7::" + name.strip().casefold()
