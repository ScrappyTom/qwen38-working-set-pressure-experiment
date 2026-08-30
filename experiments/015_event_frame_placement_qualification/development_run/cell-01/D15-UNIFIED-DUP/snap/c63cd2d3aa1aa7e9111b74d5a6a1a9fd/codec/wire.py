from codec.label import codec_label


def encode_wire(value: str) -> bytes:
    return codec_label(value).encode('ascii')
