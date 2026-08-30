from api.primary import normalize_primary
from api.secondary import normalize_secondary


def render_pair(a: str, b: str) -> str:
    return f"{normalize_primary(a)}|{normalize_secondary(b)}"
