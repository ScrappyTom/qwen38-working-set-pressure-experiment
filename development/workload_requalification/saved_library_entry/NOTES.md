# Running entry qualification notes

Initial local restore failed before runtime because older Cxx candidate snapshots
do not serialize max_file_bytes. The historical runner declares FILE_LIMIT; use
that pinned value for these exact old snapshots rather than assuming the new schema.
Preserve candidate identity and every source version. No model request occurred.
