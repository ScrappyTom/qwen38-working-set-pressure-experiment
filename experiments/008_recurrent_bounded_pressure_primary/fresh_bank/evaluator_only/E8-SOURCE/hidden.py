from dispatch.token import dispatch_token
from dispatch.badge import dispatch_badge
from dispatch.compose import compose_dispatch
assert dispatch_token(' Blue ') == 'topaz-blue'
assert dispatch_badge(' x ') == 'topaz-X'
assert compose_dispatch(' MiXeD ', ' q7 ') == 'topaz-mixed|topaz-Q7'
assert dispatch_token(' A ') == 'topaz-a'
assert dispatch_badge(' b ') == 'topaz-B'
print('hidden passed')
