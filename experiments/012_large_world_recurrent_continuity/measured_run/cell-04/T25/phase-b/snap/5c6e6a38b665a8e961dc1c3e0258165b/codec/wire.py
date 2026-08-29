from codec.label import codec_label
from codec.header import codec_header
from codec.footer import codec_footer


def encode_wire(value: str) -> bytes:
    return f"{codec_label(value)}|{codec_header(value)}|{codec_footer(value)}".encode("ascii")
