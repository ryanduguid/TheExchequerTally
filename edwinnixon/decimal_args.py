"""Fail-closed argparse helpers for Decimal money."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation


def decimal_type(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"not a decimal amount: {value!r}") from exc
    if not parsed.is_finite():
        raise argparse.ArgumentTypeError(f"not a finite decimal amount: {value!r}")
    return parsed
