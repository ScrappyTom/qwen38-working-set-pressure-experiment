from dispatch.token import dispatch_token
from dispatch.badge import dispatch_badge
assert dispatch_token(' Blue ') == 'topaz-blue'
assert dispatch_badge(' x ') == 'X'
print('phase B passed')
