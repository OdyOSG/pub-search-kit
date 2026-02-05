import pytest

from pub_search_py import Article, ArticleSearchProvider, search_across_adapters


class DummyAdapter(ArticleSearchProvider):
    def __init__(self, name: str, payload: str = "hit", *, should_raise: bool = False):
        self.name = name
        self.payload = payload
        self.should_raise = should_raise

    def search_by_keyword(self, keyword: str, *, page_size=25, max_items=None, max_pages=None):
        if self.should_raise:
            raise RuntimeError(f"{self.name} boom")
        return [
            Article(
                title=f"{self.name}:{keyword}:{self.payload}",
                abstract="abstract",
                doi=None,
                url=None,
            )
        ]


def test_search_across_adapters_returns_results_per_adapter():
    adapters = [
        DummyAdapter("A"),
        DummyAdapter("B", payload="extra"),
    ]
    results = search_across_adapters(adapters, "ibuprofen", max_items=1)
    assert set(results.keys()) == {"DummyAdapter", "DummyAdapter#2"}
    titles = {articles[0].title for articles in results.values()}
    assert titles == {"A:ibuprofen:hit", "B:ibuprofen:extra"}


def test_search_across_adapters_handles_duplicate_class_names():
    adapters = [DummyAdapter("A1"), DummyAdapter("A2")]
    results = search_across_adapters(adapters, "term")
    assert set(results.keys()) == {"DummyAdapter", "DummyAdapter#2"}
    titles = {articles[0].title for articles in results.values()}
    assert titles == {"A1:term:hit", "A2:term:hit"}


def test_search_across_adapters_propagates_exceptions():
    adapters = [DummyAdapter("good"), DummyAdapter("bad", should_raise=True)]
    with pytest.raises(RuntimeError):
        search_across_adapters(adapters, "term")
