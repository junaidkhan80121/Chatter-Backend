from typing import List


def paginate(items: List, page: int = 1, per_page: int = 20):
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], len(items)
