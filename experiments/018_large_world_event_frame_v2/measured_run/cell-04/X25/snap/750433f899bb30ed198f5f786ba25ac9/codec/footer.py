def codec_footer(value: str) -> str:
    return "HARBOR-K9::" + value.strip().casefold()
