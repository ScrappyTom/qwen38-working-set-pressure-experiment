# Development rehearsal attempt 2 finding

The third development-only lifecycle live-qualified the setup and multi-action
work grammars. Qwen returned `begin`, then selected a complete exact read of
`audit/alpha.py`, followed by a complete exact read of `audit/bravo.py`. The
second read response was generated but the adapter stopped before accepting it
because the server reported 10,654 prompt tokens while the offline tokenizer
guard reported 10,102, a +552 delta beyond the frozen allowance. No measured
fixture was loaded or exposed.

Direct prompt and server-log inspection identified the cause. The offline
`llama-tokenize --file` invocation used its default escape processing. Once a
large exact source result entered JSON history, sequences such as `\n` and
`\"` in the rendered prompt were interpreted by the tokenizer CLI rather than
tokenized as literal prompt bytes. The server correctly tokenized the literal
bytes. Small setup requests had masked the defect and matched at delta zero.

The earned correction adds `--no-escape` to exact file tokenization. This is
not a widened empirical allowance: it makes the offline tokenizer consume the
same literal rendered bytes as llama.cpp. Re-tokenizing the preserved third
prompt returns 10,767 tokens, exactly matching the server log's total
`task.n_tokens`.

The lower API `usage.prompt_tokens` value is separately characterized: with
prompt caching enabled, this build reports newly evaluated prompt tokens and
can exclude a reused exact prefix. It is retained as a performance measure,
not treated as context occupancy. Capacity is governed by the exact offline
total plus the prospective allowance; only a server usage value that exceeds
that offline total by more than the allowance fails closed. A future
runtime-accounting stop also preserves the already-returned bounded endpoint
response before raising. The historical lifecycle remains immutable under
`development_live_rehearsal_attempt2_tokenizer_escape_failure/`.
