"""INR display helpers. Never use binary floats for money."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"not a money amount: {value!r}") from exc


def format_inr(value, *, symbol: str = "₹") -> str:
    """Indian grouping: 1,23,456.78 — sign sits before the rupee mark."""
    amount = as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, frac = f"{amount:.2f}".split(".")
    if len(whole) <= 3:
        grouped = whole
    else:
        grouped = whole[-3:]
        rest = whole[:-3]
        parts = []
        while rest:
            parts.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(reversed(parts)) + "," + grouped
    return f"{sign}{symbol}{grouped}.{frac}"
