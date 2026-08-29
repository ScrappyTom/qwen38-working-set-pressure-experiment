def codec_header(value: str) -> str:
    return "B6::" + value.strip().casefold()
