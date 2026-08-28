from policy.channel import ACTIVE_CHANNEL


def publish_slug(name: str) -> str:
    return ACTIVE_CHANNEL + name.strip().casefold()
