"""Redis caching keyed by a data version. Every successful sync, merge decision or maintenance event bumps the
version, so cached API responses and exports invalidate together without tracking individual keys."""

from collections.abc import Callable

from django.core.cache import cache

VERSION_KEY = "data-version"


def data_version() -> int:
    value = cache.get(VERSION_KEY)
    if value is None:
        cache.add(VERSION_KEY, 1, timeout=None)
        value = cache.get(VERSION_KEY) or 1
    return int(value)


def bump_data_version() -> int:
    try:
        return cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, timeout=None)
        return 2


def cached(key: str, builder: Callable, timeout: int | None = 60 * 60):
    full_key = f"v{data_version()}:{key}"
    value = cache.get(full_key)
    if value is None:
        value = builder()
        cache.set(full_key, value, timeout=timeout)
    return value
