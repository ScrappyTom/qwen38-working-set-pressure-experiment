from portal.label import portal_label
from portal.header import portal_header

def encoded_portal(name: str) -> bytes:
    return f"{portal_label(name)}|{portal_header(name)}".encode('ascii')
