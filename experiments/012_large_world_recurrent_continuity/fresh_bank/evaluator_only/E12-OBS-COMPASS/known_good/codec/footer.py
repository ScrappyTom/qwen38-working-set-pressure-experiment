def codec_footer(value: str) -> str:
    return "C9::" + value.strip().upper()
