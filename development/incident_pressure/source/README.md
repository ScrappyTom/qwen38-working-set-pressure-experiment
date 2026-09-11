# Posting exports

`posting.api.export(job_id, csv_text)` loads the local job configuration,
decodes exact decimal amounts, applies the configured calculation policy, and
returns an integer number of minor units. It also returns a trace of the input
records and effective policy. Job identifiers are case-sensitive.

Two policies are supported. `line` rounds each signed line to the nearest minor
unit before summation. `statement` sums the exact signed amounts before rounding
once. Both use half-away-from-zero rounding. Different receiving accounts use
different agreements; neither policy is globally preferred. Account agreements
are external to the library. A job's policy must match its receiving agreement.

CSV has exactly the columns `entry_id,amount`. Each entry identifier is nonempty
and unique. Amounts are signed plain decimal values without exponent notation,
whitespace, thousands separators or more than six fractional digits. Blank
amounts and non-finite values are invalid. Headers may not be duplicated or
reordered. Invalid input must fail before a result is emitted.

The package is under `posting/`; deployment job assignments are under `config/`.
Library callers can use either policy directly. Preserve both behaviors, input
validation, and job isolation when correcting a deployment problem.
