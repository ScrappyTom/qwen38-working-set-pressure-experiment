from vector.label import vector_label
from vector.header import vector_header
assert vector_label(' blue ') == 'Q5^^BLUE'
assert vector_header(' X ') == 'x'
print('phase B passed')
