from packet.code import packet_code

def encoded_code(name: str) -> bytes:
    return packet_code(name).encode('ascii')
