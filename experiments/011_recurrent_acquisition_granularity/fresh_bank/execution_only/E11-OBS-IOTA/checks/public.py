from harbor.label import harbor_label
from harbor.header import harbor_header
from harbor.wire import encoded_harbor
assert harbor_label(' blue ') == 'H2@@BLUE'
assert harbor_header(' X ') == 'J7@@x'
assert encoded_harbor(' Ab ') == b'H2@@AB|J7@@ab'
print('public passed')
