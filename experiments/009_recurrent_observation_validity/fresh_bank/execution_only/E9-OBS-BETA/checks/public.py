from pulse.label import pulse_label
from pulse.header import pulse_header
from pulse.wire import encoded_pulse
assert pulse_label(' blue ') == 'L6!!BLUE'
assert pulse_header(' X ') == 'P4!!x'
assert encoded_pulse(' Ab ') == b'L6!!AB|P4!!ab'
print('public passed')
