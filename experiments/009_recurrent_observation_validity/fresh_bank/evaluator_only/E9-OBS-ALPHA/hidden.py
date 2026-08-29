from beacon.label import beacon_label
from beacon.header import beacon_header
from beacon.wire import encoded_beacon
assert beacon_label(' blue ') == 'C3%%BLUE'
assert beacon_header(' X ') == 'N9%%x'
assert encoded_beacon(' Ab ') == b'C3%%AB|N9%%ab'
assert beacon_header(' Mixed ') == 'N9%%mixed'
print('hidden passed')
