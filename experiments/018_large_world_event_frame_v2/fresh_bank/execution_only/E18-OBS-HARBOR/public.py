from codec.label import codec_label
from codec.footer import codec_footer
from codec.wire import encode_wire
assert codec_label(' a ') == 'HARBOR-K9::A'
assert codec_footer(' B ') == 'HARBOR-K9::b'
assert encode_wire(' Ab ') == 'HARBOR-K9::AB|HARBOR-K9::ab'
print('public passed')
