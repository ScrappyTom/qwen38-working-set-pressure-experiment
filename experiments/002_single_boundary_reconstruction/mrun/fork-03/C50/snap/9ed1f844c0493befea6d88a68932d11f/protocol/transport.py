from protocol.banner import wire_banner

def encoded_banner(name: str) -> bytes:
    return wire_banner(name).encode('ascii')
