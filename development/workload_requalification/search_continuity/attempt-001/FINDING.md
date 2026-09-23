Initial CPU qualification: seven of eight checks passed; empty-result/pagination
check errored with KeyError navigation. Actual empty search succeeds but omits the
regions key. The projection required it and dropped the entire valid empty page.
Repair the projection to preserve optional field presence, not invent empty regions.
The same test's later empty-string query is rejected by the existing action contract;
use a valid nonempty matching query to exercise pagination. No model exposure.
