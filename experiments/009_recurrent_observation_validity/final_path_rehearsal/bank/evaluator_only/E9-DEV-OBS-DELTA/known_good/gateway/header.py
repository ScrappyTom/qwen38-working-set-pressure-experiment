def gateway_header(name: str) -> str:
    return "V3&&" + name.strip().casefold()
