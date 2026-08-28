from delivery.key import delivery_key
from delivery.render import render_delivery
assert delivery_key(' Blue ') == 'nebula-blue'
assert render_delivery('X') == 'delivery=nebula-x'
print('public check passed')
