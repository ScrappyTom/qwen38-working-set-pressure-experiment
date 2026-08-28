from release.key import release_key

def render_key(name: str) -> str:
    return f"release={release_key(name)}"
