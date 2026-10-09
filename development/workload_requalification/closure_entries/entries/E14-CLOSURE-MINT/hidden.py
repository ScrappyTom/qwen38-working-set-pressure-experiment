from codec.label import codec_label
from codec.wire import encode_wire
assert codec_label(' a ') == 'M8::A'
assert encode_wire(' Ab ') == b'M8::AB'
print('hidden passed')
