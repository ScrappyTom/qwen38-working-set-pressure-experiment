from policy.channel import CHANNEL_STEM


def dispatch_token(name: str) -> str:
    return CHANNEL_STEM + name.strip().casefold()
