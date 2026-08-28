from session.label import session_label
from session.header import session_header
assert session_label(' blue ') == 'K4::BLUE'
assert session_header(' X ') == 'x'
print('phase B passed')
