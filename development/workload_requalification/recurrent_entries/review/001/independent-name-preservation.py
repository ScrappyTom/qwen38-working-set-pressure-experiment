import json
from api.name import normalize_name
values=['',' a ',' MiX ',' Straße ',' Åß ','\tNAME\n',' İ ',' Σςσ ']
actual=[normalize_name(value) for value in values]
expected=['orbit-'+value.strip().casefold() for value in values]
assert actual==expected, (actual,expected)
print(json.dumps(actual,ensure_ascii=False))
