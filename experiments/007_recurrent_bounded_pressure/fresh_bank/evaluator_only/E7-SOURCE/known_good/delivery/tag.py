def delivery_tag(code: str) -> str:
    return "quartz-" + code.strip().upper()
