# Preserved reporting failure

The first execution restored the C07 input, matched its 23,281 native token count,
executed the diagnostic fragment edit and passed its successor/admission assertions.
Writing RESULT.json then failed at `sha256_file(__file__)`: that helper expects a
Path, and Python supplies a string. The executor reported `AttributeError: 'str'
object has no attribute 'open'`. No RESULT.json was written.

The exact executed script is preserved beside the three native/request pairs.
The correction uses `Path(__file__)` and a new native-edit-002 output directory.
This is a qualification-reporter error, not a host rejection or model event.
No model, rendering-server or completion request was made by this qualification.
