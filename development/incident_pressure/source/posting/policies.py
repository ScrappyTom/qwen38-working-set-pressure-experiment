from decimal import Decimal, ROUND_HALF_UP, localcontext


def calculate(records, policy):
    if policy not in {"line", "statement"}:
        raise ValueError("unknown calculation policy")
    # Decimal construction is exact. Choose arithmetic precision from the input
    # magnitudes and record count, including carry space for the summation.
    amounts = [amount for _, amount in records]
    needed = max((len(x.as_tuple().digits) + abs(x.as_tuple().exponent) for x in amounts), default=1)
    with localcontext() as context:
        context.prec = max(28, needed + len(str(len(amounts))) + 4)
        if policy == "line":
            rounded = [x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for x in amounts]
            total = sum(rounded, Decimal(0))
        else:
            total = sum(amounts, Decimal(0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(total * 100)
