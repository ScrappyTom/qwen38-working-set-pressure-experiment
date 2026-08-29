from runtime.nameplate import runtime_nameplate
from runtime.prefix import runtime_prefix

def encoded_runtime(name: str) -> bytes:
    return f"{runtime_nameplate(name)}|{runtime_prefix(name)}".encode('ascii')
