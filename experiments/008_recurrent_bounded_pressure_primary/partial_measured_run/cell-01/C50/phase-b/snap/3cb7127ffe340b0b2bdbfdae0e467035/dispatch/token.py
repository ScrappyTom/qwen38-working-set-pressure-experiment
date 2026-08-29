from policy.channel import channel_stem

def dispatch_token(name: str) -> str:
    return channel_stem() + name.strip().casefold()
