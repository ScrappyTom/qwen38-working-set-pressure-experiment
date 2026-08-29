from api.name import normalize_name
from policies.current import active_policy_prefix
assert active_policy_prefix() == 'lumen-'
assert normalize_name(' Blue ') == 'lumen-blue'
print('public passed')
