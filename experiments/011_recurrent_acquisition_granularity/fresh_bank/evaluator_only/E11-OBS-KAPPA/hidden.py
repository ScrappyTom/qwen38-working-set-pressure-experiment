from vector.label import vector_label
from vector.header import vector_header
from vector.wire import encoded_vector
assert vector_label(' blue ') == 'Q5^^BLUE'
assert vector_header(' X ') == 'X8^^x'
assert encoded_vector(' Ab ') == b'Q5^^AB|X8^^ab'
assert vector_header(' Mixed ') == 'X8^^mixed'
print('hidden passed')
