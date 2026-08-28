from packet.code import packet_code
from packet.transport import encoded_code
assert packet_code(' blue ') == 'K3>BLUE'
assert encoded_code('x') == b'K3>X'
assert packet_code(' MiXeD ') == 'K3>MIXED'
print('hidden check passed')
