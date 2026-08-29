from codec.label import codec_label
from codec.header import codec_header
assert codec_label(' blue ') == 'A3::BLUE'
assert codec_header(' X ') == 'B6::x'
print('phase C passed')
