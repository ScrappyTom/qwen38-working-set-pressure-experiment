from config.frame import FRAME_PREFIX


def wire_header(name: str) -> str:
    return FRAME_PREFIX + name.strip().upper()
