from relay.label import relay_label
from relay.header import relay_header
from relay.wire import encoded_relay
assert relay_label(' blue ') == 'D5##BLUE'
assert relay_header(' X ') == 'T2##x'
assert encoded_relay(' Ab ') == b'D5##AB|T2##ab'
print('public passed')
