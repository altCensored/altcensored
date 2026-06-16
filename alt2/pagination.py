from math import ceil


class CursorPagination:
    """Pagination state for keyset (cursor) paginated listings."""
    def __init__(self, has_next, next_cursor, page=1):
        self.has_next = has_next
        self.next_cursor = next_cursor  # str | None
        self.page = page

    @property
    def has_prev(self):
        return self.page > 1


class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=1, left_current=0,
        right_current=1, right_edge=1):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
              (num > self.page - left_current - 1 and \
            num < self.page + right_current) or \
            num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num






