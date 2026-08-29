from pulse.label import pulse_label
from pulse.header import pulse_header
assert pulse_label(' blue ') == 'L6!!BLUE'
assert pulse_header(' X ') == 'x'
print('phase B passed')
