from harbor.label import harbor_label
from harbor.header import harbor_header

def encoded_harbor(name: str) -> bytes:
    return f"{harbor_label(name)}|{harbor_header(name)}".encode('ascii')
