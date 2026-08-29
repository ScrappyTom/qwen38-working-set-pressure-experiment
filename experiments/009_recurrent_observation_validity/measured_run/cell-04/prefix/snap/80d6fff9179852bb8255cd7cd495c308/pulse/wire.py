from pulse.label import pulse_label
from pulse.header import pulse_header

def encoded_pulse(name: str) -> bytes:
    return f"{pulse_label(name)}|{pulse_header(name)}".encode('ascii')
