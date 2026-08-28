from runtime.nameplate import runtime_nameplate
from runtime.prefix import runtime_prefix
assert runtime_nameplate(' blue ') == 'J2@@BLUE'
assert runtime_prefix(' X ') == 'x'
print('phase B passed')
