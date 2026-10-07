import math


def total_pages(n_items: int, per_page: int) -> int:
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return math.ceil(n_items / per_page)


def paginate(items: list, page: int, per_page: int) -> list:
    pages = total_pages(len(items), per_page)
    if page < 1 or page > pages:
        raise ValueError(f"page {page} out of range 1..{pages}")
    start = (page - 1) * per_page
    return items[start:start + per_page]
