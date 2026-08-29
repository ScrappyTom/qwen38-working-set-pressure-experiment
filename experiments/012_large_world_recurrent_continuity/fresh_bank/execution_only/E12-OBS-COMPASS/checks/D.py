from codec.label import codec_label
from codec.header import codec_header
from codec.footer import codec_footer
from codec.wire import encode_wire
assert codec_label(' blue ') == 'A3::BLUE'
assert codec_header(' X ') == 'B6::x'
assert codec_footer(' q7 ') == 'C9::Q7'
assert encode_wire(' Ab ') == b'A3::AB|B6::ab|C9::AB'
print('public passed')
