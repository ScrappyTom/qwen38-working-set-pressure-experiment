from gateway.label import gateway_label
from gateway.header import gateway_header
from gateway.wire import encoded_gateway
assert gateway_label(' blue ') == 'F7&&BLUE'
assert gateway_header(' X ') == 'V3&&x'
assert encoded_gateway(' Ab ') == b'F7&&AB|V3&&ab'
print('public passed')
