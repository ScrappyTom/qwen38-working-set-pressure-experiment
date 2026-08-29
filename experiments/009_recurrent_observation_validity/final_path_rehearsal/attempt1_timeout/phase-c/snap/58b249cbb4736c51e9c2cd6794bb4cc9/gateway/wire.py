from gateway.label import gateway_label
from gateway.header import gateway_header

def encoded_gateway(name: str) -> bytes:
    return f"{gateway_label(name)}|{gateway_header(name)}".encode('ascii')
