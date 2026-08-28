from release.tag import release_tag
from release.formatting import display_tag
assert release_tag('  Blue  ') == 'stable-blue'
assert display_tag(release_tag('X')) == 'release=stable-x'
print('public check passed')
assert release_tag(' MiXeD ') == 'stable-mixed'
print('hidden check passed')
