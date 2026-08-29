from vector.label import vector_label
from vector.header import vector_header

def encoded_vector(name: str) -> bytes:
    return f"{vector_label(name)}|{vector_header(name)}".encode('ascii')
