from portal.label import portal_label
from portal.header import portal_header
from portal.wire import encoded_portal
assert portal_label(' blue ') == 'G8++BLUE'
assert portal_header(' X ') == 'W6++x'
assert encoded_portal(' Ab ') == b'G8++AB|W6++ab'
assert portal_header(' Mixed ') == 'W6++mixed'
print('hidden passed')
