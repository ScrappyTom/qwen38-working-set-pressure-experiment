from session.label import session_label
from session.header import session_header
from session.wire import encoded_session
assert session_label(' blue ') == 'K4::BLUE'
assert session_header(' X ') == 'M7::x'
assert encoded_session(' Ab ') == b'K4::AB|M7::ab'
print('public passed')
