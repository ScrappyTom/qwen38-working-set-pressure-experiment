from api.name import normalize_name
from api.footer import normalize_footer


def render_identity(name: str, footer: str) -> str:
    return f"{normalize_name(name)}|{normalize_footer(footer)}"
