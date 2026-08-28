from release.key import release_key
from release.render import render_key
assert release_key('  Blue  ') == 'orb/blue'
assert render_key('X') == 'release=orb/x'
print('public check passed')
