from session.label import session_label
from session.header import session_header

def encoded_session(name: str) -> bytes:
    return f"{session_label(name)}|{session_header(name)}".encode('ascii')
