from session.label import session_label
from session.wire import encoded_label
assert session_label(' blue ') == 'K4::BLUE'
assert encoded_label('x') == b'K4::X'
print('public check passed')
