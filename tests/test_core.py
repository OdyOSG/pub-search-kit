import pytest

from pub_search_py.core import Article, choose_best_url, normalize_doi


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("10.1000/ABC123", "10.1000/abc123"),
        ("https://doi.org/10.1000/ABC123", "10.1000/abc123"),
        ("HTTPS://DX.DOI.ORG/10.5555/XYZ", "10.5555/xyz"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_doi(raw, expected):
    assert normalize_doi(raw) == expected


def test_choose_best_url_prefers_pmc_then_doi_then_first():
    urls = [
        "https://example.org/foo",
        "https://doi.org/10.1/abc",
        "https://pmc.ncbi.nlm.nih.gov/article/PMC123",
    ]
    assert choose_best_url(urls) == "https://pmc.ncbi.nlm.nih.gov/article/PMC123"

    urls = [
        "https://example.org/foo",
        "https://doi.org/10.1/abc",
    ]
    assert choose_best_url(urls) == "https://doi.org/10.1/abc"

    urls = ["https://example.org/foo", None]
    assert choose_best_url(urls) == "https://example.org/foo"


def test_article_dataclass_repr():
    art = Article(title="t", abstract="a", doi=None, url=None)
    assert "title='t'" in repr(art)
