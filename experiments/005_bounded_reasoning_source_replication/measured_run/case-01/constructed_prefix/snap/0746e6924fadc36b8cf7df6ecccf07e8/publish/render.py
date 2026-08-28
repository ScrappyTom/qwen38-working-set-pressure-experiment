from publish.slug import publish_slug

def render_slug(name: str) -> str:
    return f"publish={publish_slug(name)}"
