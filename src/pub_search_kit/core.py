from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol, runtime_checkable
import re


@dataclass(frozen=True)
class Article:
    """Normalized representation of an article/record."""

    title: str
    url: Optional[str]
    doi: Optional[str]
    abstract: str


@runtime_checkable
class ArticleSearchProvider(Protocol):
    """Protocol implemented by every adapter in this package."""

    def search_by_keyword(
        self,
        keyword: str,
        *,
        page_size: int = 25,
        max_items: Optional[int] = 200,
        max_pages: Optional[int] = None,
    ) -> List[Article]:
        """Return `Article` entries that match *keyword*."""


_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Strip resolver prefixes and lowercase DOIs for stable comparisons."""

    if not doi:
        return None
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.IGNORECASE)
    if not normalized:
        return None
    if not _DOI_RE.search(normalized):
        return normalized.lower()
    return normalized.lower()


def choose_best_url(urls: Iterable[Optional[str]]) -> Optional[str]:
    """Pick the most stable URL among PMC, DOI, PubMed, etc."""

    cleaned = [u for u in urls if u]
    if not cleaned:
        return None
    for candidate in cleaned:
        if candidate.startswith("https://pmc.ncbi.nlm.nih.gov/"):
            return candidate
    for candidate in cleaned:
        if candidate.startswith("https://doi.org/"):
            return candidate
    return cleaned[0]


__all__ = [
    "Article",
    "ArticleSearchProvider",
    "normalize_doi",
    "choose_best_url",
]
