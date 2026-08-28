from delivery.key import delivery_key
from delivery.tag import delivery_tag

def render_delivery(name: str, code: str) -> str:
    return f"{delivery_key(name)}|{delivery_tag(code)}"
