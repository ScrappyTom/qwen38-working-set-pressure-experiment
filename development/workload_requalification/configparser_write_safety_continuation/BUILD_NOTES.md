# Implementation notes

The first CPU test import failed because the thin bootstrap did not expose ROOT,
which the reused dispatch module expects. Added that existing path binding; no
runtime or model request occurred. The frozen prior task remains unchanged.

The checker correction removes exactly one asserted source line. Its positive
fixture changes exception wording while preserving the write guard; negatives
retain unsafe writing, vacuous regression coverage and omitted documentation.
