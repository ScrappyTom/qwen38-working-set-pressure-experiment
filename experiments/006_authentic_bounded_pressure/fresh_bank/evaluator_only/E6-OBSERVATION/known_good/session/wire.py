from session.label import session_label

def encoded_label(name: str) -> bytes:
    return session_label(name).encode('ascii')
