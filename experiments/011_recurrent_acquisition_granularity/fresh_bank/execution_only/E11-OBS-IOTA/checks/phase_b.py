from harbor.label import harbor_label
from harbor.header import harbor_header
assert harbor_label(' blue ') == 'H2@@BLUE'
assert harbor_header(' X ') == 'x'
print('phase B passed')
