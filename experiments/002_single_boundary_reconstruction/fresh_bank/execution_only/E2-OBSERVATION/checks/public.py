from protocol.banner import wire_banner
from protocol.transport import encoded_banner
assert wire_banner(' blue ') == 'XP9:BLUE'
assert encoded_banner('x') == b'XP9:X'
print('public check passed')
