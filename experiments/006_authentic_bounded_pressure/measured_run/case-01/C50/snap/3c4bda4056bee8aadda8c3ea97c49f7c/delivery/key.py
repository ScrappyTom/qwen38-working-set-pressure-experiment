from policy.route import route_stem

def delivery_key(name: str) -> str:
    return route_stem() + name.strip().casefold()
