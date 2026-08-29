from gateway.label import gateway_label
from gateway.header import gateway_header
assert gateway_label(' blue ') == 'F7&&BLUE'
assert gateway_header(' X ') == 'x'
print('phase B passed')
