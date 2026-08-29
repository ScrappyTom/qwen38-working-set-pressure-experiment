from codec.label import codec_label
from codec.header import codec_header
from codec.footer import codec_footer
from codec.wire import encode_wire
assert codec_label(' a ') == 'A3::A'
assert codec_header(' B ') == 'B6::b'
assert codec_footer(' c ') == 'C9::C'
assert encode_wire(' Ab ') == b'A3::AB|B6::ab|C9::AB'
print('hidden passed')
