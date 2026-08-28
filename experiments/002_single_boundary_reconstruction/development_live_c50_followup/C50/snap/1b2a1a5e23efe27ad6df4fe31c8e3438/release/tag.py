from policy.channel import release_prefix


def release_tag(name: str) -> str:
    return f"{release_prefix()}{name.strip().lower()}"
