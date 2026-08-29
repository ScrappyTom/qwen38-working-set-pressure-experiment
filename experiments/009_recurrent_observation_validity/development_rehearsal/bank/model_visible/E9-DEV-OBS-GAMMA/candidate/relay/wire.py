from relay.label import relay_label
from relay.header import relay_header

def encoded_relay(name: str) -> bytes:
    return f"{relay_label(name)}|{relay_header(name)}".encode('ascii')
