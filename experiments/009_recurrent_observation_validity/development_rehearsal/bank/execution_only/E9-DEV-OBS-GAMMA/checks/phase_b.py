from relay.label import relay_label
from relay.header import relay_header
assert relay_label(' blue ') == 'D5##BLUE'
assert relay_header(' X ') == 'x'
print('phase B passed')
