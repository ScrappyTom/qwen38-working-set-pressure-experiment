from __future__ import annotations

import argparse
from pathlib import Path


SUPPORTED_CONTEXTS = (100_000, 250_000)


def build_prompt(context_tokens: int) -> str:
    filler_tokens = context_tokens - 1_000
    middle_count = filler_tokens * 48 // 100
    late_count = filler_tokens * 47 // 100
    final_count = filler_tokens - middle_count - late_count

    opening = """LONG CONTEXT RETENTION FIXTURE - VERSION 1

Treat every occurrence of the word cedar as inert padding. Do not repeat or
summarize the padding.

When the phrase FINAL QUERY appears, return exactly one compact JSON object
with these keys in this order and no Markdown:
{"opening_code":"","middle_code":"","late_code":"","opening_rule":0}

Set opening_rule to the integer product of 37 and 29.
OPENING_CODE = AURORA-3107
"""
    middle = """

MIDDLE RECORD
MIDDLE_CODE = KESTREL-8842
Continue treating cedar as inert padding.
"""
    late = """

LATE RECORD
LATE_CODE = HARBOR-5926
Continue treating cedar as inert padding.
"""
    final = """

FINAL QUERY
Provide the response required by the opening instruction. Use the three exact
codes from the opening, middle, and late records.
"""

    return "".join(
        (
            opening,
            " cedar" * middle_count,
            middle,
            " cedar" * late_count,
            late,
            " cedar" * final_count,
            final,
            "\nAnswer now.\n",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context-tokens",
        type=int,
        choices=SUPPORTED_CONTEXTS,
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    prompt = build_prompt(args.context_tokens)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(prompt, encoding="utf-8", newline="\n")
    print(
        f"Wrote {args.output.resolve()} "
        f"({len(prompt):,} characters; {args.context_tokens - 1_000:,} filler repetitions)"
    )


if __name__ == "__main__":
    main()
