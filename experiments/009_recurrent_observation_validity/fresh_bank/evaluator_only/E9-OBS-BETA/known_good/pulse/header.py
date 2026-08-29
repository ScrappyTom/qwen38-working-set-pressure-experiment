def pulse_header(name: str) -> str:
    return "P4!!" + name.strip().casefold()
