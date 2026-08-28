from publish.slug import publish_slug
from publish.formatting import display_slug
assert publish_slug('  Blue  ') == 'gold-blue'
assert display_slug(publish_slug('X')) == 'publish=gold-x'
assert publish_slug(' MiXeD ') == 'gold-mixed'
print('hidden check passed')
