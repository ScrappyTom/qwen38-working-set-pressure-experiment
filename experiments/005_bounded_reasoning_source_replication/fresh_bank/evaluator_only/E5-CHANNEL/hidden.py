from publish.slug import publish_slug
from publish.render import render_slug
assert publish_slug(' Blue ') == 'quartz/blue'
assert render_slug('X') == 'publish=quartz/x'
assert publish_slug(' MiXeD ') == 'quartz/mixed'
print('hidden check passed')
