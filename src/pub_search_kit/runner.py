from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Optional

from .core import Article, ArticleSearchProvider


def search_across_adapters(
    adapters: Iterable[ArticleSearchProvider],
    keyword: str,
    *,
    page_size: int = 25,
    max_items: Optional[int] = 200,
    max_pages: Optional[int] = None,
    max_workers: Optional[int] = None,
) -> Dict[str, List[Article]]:
    """
    Search a keyword across multiple adapters in parallel.

    Args:
        adapters: Iterable of configured ArticleSearchProvider instances.
        keyword: Search term passed to every adapter.
        page_size: Per-adapter `page_size`.
        max_items: Per-adapter `max_items`.
        max_pages: Per-adapter `max_pages`.
        max_workers: Optional override for the thread pool size. Defaults to
            `len(adapters)` (or 1 if no adapters).

    Returns:
        Dict mapping adapter class name to list of Article results. If an adapter
        raises an exception, the exception is re-raised after cancelling remaining futures.
    """

    adapter_list = list(adapters)
    if not adapter_list:
        return {}

    workers = max_workers or len(adapter_list) or 1
    results: Dict[str, List[Article]] = {}
    name_counts: Dict[str, int] = {}

    def _run(provider: ArticleSearchProvider) -> List[Article]:
        return provider.search_by_keyword(
            keyword,
            page_size=page_size,
            max_items=max_items,
            max_pages=max_pages,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map: Dict[Future[List[Article]], ArticleSearchProvider] = {}
        for adapter in adapter_list:
            future = pool.submit(_run, adapter)
            future_map[future] = adapter

        for future in as_completed(future_map):
            adapter = future_map[future]
            adapter_name = adapter.__class__.__name__
            try:
                articles = future.result()
            except Exception:
                # Cancel outstanding futures before bubbling up the error.
                for pending in future_map:
                    if not pending.done():
                        pending.cancel()
                raise
            count = name_counts.get(adapter_name, 0)
            key = adapter_name if count == 0 else f"{adapter_name}#{count + 1}"
            results[key] = articles
            name_counts[adapter_name] = count + 1

    return results


__all__ = ["search_across_adapters"]
