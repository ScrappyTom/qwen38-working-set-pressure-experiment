"""Canonical forms for imported receipt fields."""
import re


def identifier(value: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError("empty identifier")
    return result


def label(value: str) -> str:
    return identifier(value).upper()


def number(value: str, minimum: int) -> int:
    text = value.strip()
    if re.fullmatch(r"[0-9]+", text) is None:
        raise ValueError("invalid integer")
    result = int(text)
    if result < minimum:
        raise ValueError("integer below minimum")
    return result


def status(value: str) -> str:
    result = value.strip().lower()
    if result not in {"active", "void"}:
        raise ValueError("unknown status")
    return result
