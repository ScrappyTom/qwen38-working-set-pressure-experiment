from api.name import normalize_name
from policies.current import active_policy_prefix
assert active_policy_prefix() == 'orbit-'
assert normalize_name(' Blue ') == 'orbit-blue'
print('phase B passed')
