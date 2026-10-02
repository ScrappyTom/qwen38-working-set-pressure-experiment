# Preserved qualification namespace failure

preparation-001 closed failed with zero model completions. Native36-case grammar
qualification passed and direct scripted work completed. The second independent
history produced a different EVT0007 diff; run-wide immutable diff addresses
correctly refused overwrite, stopping its final snapshot. Scoped snapshot stems
did not scope those diff paths.

qualification_route.py here is the exact failed source, recovered by reversing
the namespace patch and checked against preparation-001/SEAL.json. Its SHA256 is
ec77e930c112e7c7bdac906f2805edbb07f9e4416d1896b2f3c560cd9664febf.
All other failed preparation source bindings still match the current files.
This is a qualification-apparatus error, not a Qwen or production archive failure.
