from runtime.nameplate import runtime_nameplate
from runtime.prefix import runtime_prefix
from runtime.codec import encoded_runtime
assert runtime_nameplate(' blue ') == 'J2@@BLUE'
assert runtime_prefix(' X ') == 'R8@@x'
assert encoded_runtime(' Ab ') == b'J2@@AB|R8@@ab'
print('public passed')
