from delivery.key import delivery_key

def render_delivery(name: str) -> str:
    return f"delivery={delivery_key(name)}"
