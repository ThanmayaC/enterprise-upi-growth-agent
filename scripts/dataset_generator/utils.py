"""
utils.py

Shared, reusable helper functions used across generator modules.
No business-rule logic lives here — only mechanical helpers
(ID generation, formatting, RNG helpers, CSV IO).
"""

from __future__ import annotations

import csv
import random
import string
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta, date, time
from pathlib import Path
from typing import Any, Iterable, Sequence


def seeded_random(seed: int) -> random.Random:
    """Return a dedicated Random instance seeded deterministically.

    Using a dedicated instance (rather than the global random module)
    keeps generation deterministic even when multiple generators run
    in the same process in an unpredictable call order.
    """
    return random.Random(seed)


def derive_sub_seed(base_seed: int, salt: str) -> int:
    """Derive a deterministic sub-seed from a base seed and a string salt.

    Ensures different generator components get different — but
    reproducible — random streams from a single RANDOM_SEED.
    """
    h = 0
    for ch in salt:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (base_seed * 1_000_003 + h) & 0xFFFFFFFF


def random_alphanumeric(rng: random.Random, length: int) -> str:
    """Generate a random uppercase alphanumeric string of given length."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(rng.choice(alphabet) for _ in range(length))


def generate_txnid(rng: random.Random) -> str:
    """Generate a unique-looking alphanumeric transaction id (<=40 chars)."""
    return f"TXN{random_alphanumeric(rng, 30)}"


def generate_umn(rng: random.Random) -> str:
    """Generate a unique UPI Mandate Number in a standard-looking UMN shape.

    Real UMNs look like: <12-digit-seed>@<tag>@<random-tail>.
    We synthesize a compliant-looking but clearly synthetic value,
    kept within 50 chars per the schema's UMN column width.
    """
    digits = "".join(rng.choice(string.digits) for _ in range(12))
    tail = random_alphanumeric(rng, 8)
    return f"{digits}@UMN@{tail}"


def generate_custrefno(rng: random.Random) -> str:
    """Generate a customer reference number (<=40 chars)."""
    return f"CRN{random_alphanumeric(rng, 20)}"


def generate_indian_mobile(rng: random.Random) -> str:
    """Generate a plausible 10-digit Indian mobile number (starts 6-9)."""
    first = rng.choice("6789")
    rest = "".join(rng.choice(string.digits) for _ in range(9))
    return first + rest


def build_vpa(handle_local_part: str, bank_or_psp_handle: str) -> str:
    """Compose a VPA (Virtual Payment Address) string, e.g. name@okhdfcbank."""
    return f"{handle_local_part}@{bank_or_psp_handle}"


def random_datetime_between(rng: random.Random, start: date, end: date) -> datetime:
    """Return a uniformly random datetime between two dates (inclusive)."""
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    delta_seconds = int((end_dt - start_dt).total_seconds())
    offset = rng.randint(0, max(delta_seconds, 0))
    return start_dt + timedelta(seconds=offset)


def weighted_choice(rng: random.Random, options: Sequence[Any], weights: Sequence[float]) -> Any:
    """Pick one element from options according to the given weights."""
    return rng.choices(options, weights=weights, k=1)[0]


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    return max(low, min(high, value))


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_dicts_to_csv(path: Path, rows: Iterable[dict], fieldnames: Sequence[str]) -> None:
    """Write an iterable of dicts to a CSV file with a fixed column order.

    Missing keys in a row are written as empty strings; this keeps the
    schema's field order authoritative regardless of dict construction order.
    """
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})


def write_dataclasses_to_csv(path: Path, rows: Iterable[Any]) -> None:
    """Write an iterable of dataclass instances to CSV using their field order."""
    rows = list(rows)
    if not rows:
        ensure_dir(path.parent)
        path.touch()
        return
    sample = rows[0]
    if not is_dataclass(sample):
        raise TypeError("write_dataclasses_to_csv requires dataclass instances")
    fieldnames = [f.name for f in fields(sample)]
    dict_rows = ({f: getattr(r, f) for f in fieldnames} for r in rows)
    write_dicts_to_csv(path, dict_rows, fieldnames)


def format_ts(dt: datetime) -> str:
    """Format a datetime as YYYY-MM-DD HH:MM:SS as required by the schema."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(d: date) -> str:
    """Format a date as YYYY-MM-DD as required by the schema."""
    return d.strftime("%Y-%m-%d")


def next_business_like_offset(rng: random.Random, low_seconds: int, high_seconds: int) -> timedelta:
    """Return a small random forward time offset, used to order lifecycle events."""
    return timedelta(seconds=rng.randint(low_seconds, high_seconds))
