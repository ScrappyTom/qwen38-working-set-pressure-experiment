from delivery.key import delivery_key
from delivery.tag import delivery_tag
assert delivery_key(' Blue ') == 'quartz-blue'
assert delivery_tag(' x ') == 'X'
print('phase B passed')
