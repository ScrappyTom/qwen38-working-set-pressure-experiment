from policy.current import active_prefix
from api.primary import normalize_primary
from api.secondary import normalize_secondary
from api.render import render_pair
assert active_prefix() == 'quartz-'
assert normalize_primary(' A ') == 'ember-a'
assert normalize_secondary(' b7 ') == 'quartz-B7'
assert render_pair(' Mix ', ' q2 ') == 'ember-mix|quartz-Q2'
print('public passed')
