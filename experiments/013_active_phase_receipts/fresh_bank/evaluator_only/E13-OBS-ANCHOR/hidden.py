from codec.label import codec_label
from codec.wire import encode_wire
assert codec_label(' a ') == 'D4::A'
assert encode_wire(' Ab ') == b'D4::AB'
print('hidden passed')
