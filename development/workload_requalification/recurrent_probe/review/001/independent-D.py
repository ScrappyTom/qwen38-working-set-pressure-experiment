from workflow.progress import completed_phases
assert completed_phases()==1
values=['',' a ',' MiX ',' Straße ',' Åß ','\tNAME\n',' İ ',' Σςσ ']
from codec.label import codec_label
for value in values: assert codec_label(value)=='A3::'+value.strip().upper()
from codec.header import codec_header
for value in values: assert codec_header(value)=='B6::'+value.strip().casefold()
from codec.footer import codec_footer
from codec.wire import encode_wire
for value in values:
 assert codec_footer(value)=='C9::'+value.strip().upper()
 combined=codec_label(value)+'|'+codec_header(value)+'|'+codec_footer(value)
 if combined.isascii(): assert encode_wire(value)==combined.encode('ascii')
print('independent normalization/preservation examples passed')
