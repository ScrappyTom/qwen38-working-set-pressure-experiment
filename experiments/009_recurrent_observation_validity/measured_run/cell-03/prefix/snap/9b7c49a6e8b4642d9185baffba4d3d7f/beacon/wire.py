from beacon.label import beacon_label
from beacon.header import beacon_header

def encoded_beacon(name: str) -> bytes:
    return f"{beacon_label(name)}|{beacon_header(name)}".encode('ascii')
