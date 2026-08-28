def release_tag(name: str) -> str:
    return "stable-" + name.strip().lower()
