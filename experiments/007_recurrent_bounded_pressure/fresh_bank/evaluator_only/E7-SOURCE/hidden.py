from delivery.key import delivery_key
from delivery.tag import delivery_tag
from delivery.render import render_delivery
assert delivery_key(' Blue ') == 'quartz-blue'
assert delivery_tag(' x ') == 'quartz-X'
assert render_delivery(' MiXeD ', ' q7 ') == 'quartz-mixed|quartz-Q7'
assert delivery_key(' A ') == 'quartz-a'
assert delivery_tag(' b ') == 'quartz-B'
print('hidden passed')
