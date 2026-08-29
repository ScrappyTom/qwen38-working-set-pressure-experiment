from api.name import normalize_name
from policies.current import active_policy_prefix
assert normalize_name(' Blue ') == 'orbit-blue'
assert active_policy_prefix() == 'zenith-'
print('phase C passed')
