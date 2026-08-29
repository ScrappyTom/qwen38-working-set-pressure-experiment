from dispatch.token import dispatch_token
from dispatch.badge import dispatch_badge

def compose_dispatch(name: str, code: str) -> str:
    return f"{dispatch_token(name)}|{dispatch_badge(code)}"
