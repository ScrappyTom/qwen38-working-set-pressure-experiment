# Offline source-verification timing

Four interleaved full-hash trials over the completed prose run's6897 frozen bindings
all verify exactly. No model/server/checker ran during the profile. Four workers
averaged10.437 seconds; eight averaged9.552 seconds. This measures the
verification function itself, and supports its substantial contribution to the
approximately ten-second validation intervals observed in the prior task records.

This small single-machine timing exercise does not measure full task improvement.
Eight workers retain full hashing but save less than one second per sampled call.
The active next qualification keeps the existing four-worker configuration; no
cache, skipped source or asynchronous unverified action was introduced. The results
and exact helper/script/manifest hashes are in qualification-001/RESULTS.json.

A larger reduction would require changing when or which dependencies are verified.
That is a separate integrity decision, not justified solely by this timing result.
The current priority is finishing corpus portability and useful work. Preserve
apparatus time as a distinct cost rather than attributing it all to model requests.
