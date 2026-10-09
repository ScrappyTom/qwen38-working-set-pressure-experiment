from workflow.progress import completed_phases
assert completed_phases()==1
values=['',' a ',' MiX ',' Straße ',' Åß ','\tNAME\n',' İ ',' Σςσ ']
from codec.label import codec_label
for value in values: assert codec_label(value)=='A3::'+value.strip().upper()
print('independent normalization/preservation examples passed')
