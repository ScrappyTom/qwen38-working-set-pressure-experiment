from wire.header import wire_header
from wire.encode import encoded_header
assert wire_header(' blue ') == 'm7:BLUE'
assert encoded_header('x') == b'm7:X'
print('public check passed')
