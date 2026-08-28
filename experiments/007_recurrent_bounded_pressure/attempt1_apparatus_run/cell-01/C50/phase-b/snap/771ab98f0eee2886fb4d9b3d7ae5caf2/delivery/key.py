from policy.route import ROUTE_STEM


def delivery_key(name: str) -> str:
    return ROUTE_STEM + name.strip().casefold()
