from release.key import release_key
from release.render import render_key
assert release_key('  Blue  ') == 'orb/blue'
assert render_key('X') == 'release=orb/x'
assert release_key(' MiXeD ') == 'orb/mixed'
print('hidden check passed')
