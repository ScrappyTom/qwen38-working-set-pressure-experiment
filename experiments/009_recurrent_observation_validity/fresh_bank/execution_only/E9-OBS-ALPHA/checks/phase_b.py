from beacon.label import beacon_label
from beacon.header import beacon_header
assert beacon_label(' blue ') == 'C3%%BLUE'
assert beacon_header(' X ') == 'x'
print('phase B passed')
