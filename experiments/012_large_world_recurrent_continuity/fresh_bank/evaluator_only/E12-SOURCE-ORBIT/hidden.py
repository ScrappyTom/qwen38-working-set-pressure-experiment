from api.name import normalize_name
from api.footer import normalize_footer
from api.render import render_identity
from policies.current import active_policy_prefix
assert active_policy_prefix() == 'zenith-'
assert normalize_name(' A ') == 'orbit-a'
assert normalize_footer(' b9 ') == 'zenith-B9'
assert render_identity(' MiXeD ', ' q2 ') == 'orbit-mixed|zenith-Q2'
print('hidden passed')
