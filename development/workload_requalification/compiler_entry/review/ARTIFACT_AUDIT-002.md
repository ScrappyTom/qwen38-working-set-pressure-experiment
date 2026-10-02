# Compiler run-002 artifact audit: unchanged work, incomplete task

The run closed as operator_stopped after 14 requests and 20 recorded operations.
No repair or report contribution was saved, no check executed, and no submission
occurred. This audit establishes exact preservation of the original six files.
It does not establish artifact quality improvement or task success.

## Evidence and exact execution identity

I directly compared the original sealed candidate's file bodies with both the
actual run starting snapshot and final snapshot. I verified the individual file
digests, the selected run artifacts against RESPONSE_SEAL.json, and the original
task/checker/capture bindings against the executed manifest. I also parsed all 14
complete public final replies and the final state's 20 operation records. No
checker, application code, model, or tokenization call was executed for this audit.

The exact original execution manifest is
development/workload_requalification/compiler_entry/EXECUTION_MANIFEST-002.json.
It is byte-identical to run-002/EXECUTION_MANIFEST.json (47,404 bytes), with SHA256
`1ecaec468eb5ec457ae0a12793b1f5a4b2dadec4f4a434a07d49bf597ba2255b`.
It binds preparation-002/SEAL.json at
`8a1705aacbaeb7a3ddcd1f88007d96d844d2459fcd3c8641077a91d5bd99c4e5`,
40 maximum requests, 100 operations, seed 961221, and medium uncapped thinking.
The initial exact wire request digest is
`9dd7d3ae8202055f4a7978b57143372e62aa2afc5324c918c869848346eaa269`;
its recorded native input is 5,737 tokens with digest
`e0a5283afb836e0150dbc92d0180fce5778f27ce8000307d2da969d8b17adae2`.

The manifest's original-world bindings, checked against the actual files, are:

| Original preparation-001 artifact | SHA256 |
| --- | --- |
| TASK.txt | `469cf1b592326122c0e46bafd3e4143b288a308688615a6f4b54503839be4090` |
| candidate.json | `d11c509666bff3350a2c56f703facd991505b1adabfe0db7fa62d1fd913d3fce` |
| PUBLIC_CHECK.py | `23d69d6a42e0f8bfd34ac0ea83c14e533ab549cae67d9755b3f0126f2e39446a` |
| captures.json | `07adce4756350c3527fa7eff34ad5fc90bb05daf3404b3c7fba0dd469c9aa92e` |
| observations.json | `fe67f10081d15d1fdaa301424c7e680c0706cb6b46ce67c762e5a5455d671a51` |

The original PREPARATION_SEAL.json digest is
`35a53de9d8ca5a1811d842378d309f291035d11172791ead0d59b3ee99fe9480`.
The closed run RESPONSE_SEAL.json digest is
`6163b5fea818e51c1fdd60dd920d89ed32867eaba767b066685261f46dce2042`.
Both run starting-candidate.json and final-candidate.json are 4,741 bytes with
digest `4ddc2a2ea970ac29f4342b0dc4d8f481598620d958da6c6cb7f98d2807e462f6`;
they are byte-identical. The run serializer adds max_file_bytes and per-file
size_bytes to the older snapshot format. Therefore the original and run snapshot
JSON digests differ while the actual six file bodies are byte-identical.

The final-state.json digest is
`3d014f10a578a6b0cd992cc1f283d10fec0be6845af167f70549254e7dae5b99`.
The records.jsonl digest is
`5afc2674aea45e349eb60faa077616d23f8dbdc7f08127d4c9361bcad1c92a7f`.
The separate exact-replay report VERIFICATION-002.json has digest
`f576629551a84784183b248def2c68e8efcf5b3abb208e3fea314d2c679b7eff`.
It records replayed_exactly, 14 completed replies, 20 operations, no checks, no
additional checker/model/tokenization execution, and the same executed-manifest
digest. This artifact audit uses that completed replay as supporting custody
evidence; it does not claim to rerun the complete replay independently.

## Actual candidate preservation

Original, run-starting, and final candidate identities are all
`28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d`.
The complete path sets match. There are no added, deleted, or modified files.

| File | Bytes | Original = starting = final SHA256 |
| --- | ---: | --- |
| README.md | 2192 | `7e4f921c8ef626410cd58dcc3a749a232dc2752e7d37d4c3c161d078ecaed6b6` |
| compiler/__init__.py | 49 | `0b7c7e069b3dd37d4721eea1d1ed3b834002d9c92e974067726966c19a5f9395` |
| compiler/api.py | 688 | `a213afbff4a104cd3a4730326e9e77ab768febda1f4290e95e0ff71afc89f1db` |
| compiler/selection.py | 458 | `f6ff2ebeedf8cdea28c2f1b37858e1da8932ee0b49cf571d4c5f3c1e9750c611` |
| compiler/unary.py | 263 | `95544cb49ffb5b5e11f09991917e0028918e679fd7f9d164f63ea36b012d2e80` |
| reports/incident.json | 15 | `22efad348a13802b9bc50b72ff44cdb2234b2c9faacc9f4b33ddaea77ea68509` |

The report remains the exact bytes `{"builds": []}\n`. Neither emitted build has
a saved report row. compiler/unary.py retains its original unconditional removal
of UAdd and USub nodes. No repair has changed that implementation. Preservation
of this starting artifact is not correctness: the known defect and incomplete
report remain outstanding.

## No contemplated draft was executed

The final state's diffs map is empty and submitted is false. Its operation list
contains two tree requests, three source reads, nine imported-observation
retrievals, and six model-account records. Every recorded operation was accepted,
but none was patch, replace_region, check, or submit. The sealed run contains no
checker observation files.

All 14 complete public final replies likewise request only acquisition operations,
with six accompanying account updates. They contain no public edit, check, or
submission operation. Together with the unchanged snapshots and empty diffs,
this establishes that contemplated source/report drafts in archived deliberation
were not turned into executed work. Accounts and private reasoning are not saved
candidate edits. This audit does not claim to evaluate the correctness of every
private draft or every account statement.

Against ARTIFACT_CRITERIA.md, both substantive contribution obligations therefore
remain incomplete: repair the optimizer and save the observed two-build report.
No current repair-verification result or checked submission was produced. The
successful outcome established here is custody/preservation only, not successful
completion of the compiler task.
