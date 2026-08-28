RELEASE_GROUPS = ("amber", "cobalt", "ivory", "namespace")


def released_count() -> int:
    return len(RELEASE_GROUPS)
