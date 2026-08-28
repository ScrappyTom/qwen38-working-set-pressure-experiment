from wire.header import wire_header
from wire.transport import encoded_header
assert wire_header(' blue ') == 'R7|BLUE'
assert encoded_header('x') == b'R7|X'
assert wire_header(' MiXeD ') == 'R7|MIXED'
print('hidden check passed')
