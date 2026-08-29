from policy.channel import channel_stem

def dispatch_badge(code: str) -> str:
    return channel_stem() + code.strip().upper()
