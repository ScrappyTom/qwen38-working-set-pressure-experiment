from codec.label import codec_label
from codec.footer import codec_footer


def encode_wire(value: str) -> str:
    return f"{codec_label(value)}|{codec_footer(value)}"
