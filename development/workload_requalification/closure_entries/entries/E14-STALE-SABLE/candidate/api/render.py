from api.name import normalize_name


def render_name(value: str) -> str:
    return normalize_name(value)
