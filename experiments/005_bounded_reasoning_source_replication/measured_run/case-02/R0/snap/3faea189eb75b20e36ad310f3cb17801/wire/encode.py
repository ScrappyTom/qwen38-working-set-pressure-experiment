from wire.header import wire_header

def encoded_header(name: str) -> bytes:
    return wire_header(name).encode('ascii')
