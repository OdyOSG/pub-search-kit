from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class SemanticScholarSearchAdapter(ArticleSearchProvider):
    """Adapter for the Semantic Scholar Graph API."""

    SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    MAX_LIMIT = 100

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        timeout_s: float = 10.0,
        polite_delay_s: float = 0.0,
        session: Optional[requests.Session] = None,
        user_agent: str = "SemanticScholarArticleSearch/1.0",
        max_retries_429: int = 3,
    ) -> None:
        self.timeout_s = float(timeout_s)
        self.polite_delay_s = float(polite_delay_s)
        self.max_retries_429 = int(max_retries_429)
        self._session = session or requests.Session()
        self._own_session = session is None
        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        if api_key:
            headers["x-api-key"] = api_key.strip()
        self._session.headers.update(headers)

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _safe_str(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""

    def _get_with_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        backoff = 0.6
        for attempt in range(self.max_retries_429 + 1):
            resp = self._session.get(self.SEARCH_URL, params=params, timeout=self.timeout_s)
            if resp.status_code != 429:
                resp.raise_for_status()
                return resp.json()

            if attempt == self.max_retries_429:
                resp.raise_for_status()

            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(int(retry_after))
            else:
                time.sleep(backoff)
                backoff *= 2
        return {}

    def search_by_keyword(
        self,
        keyword: str,
        *,
        page_size: int = 25,
        max_items: Optional[int] = 200,
        max_pages: Optional[int] = None,
    ) -> List[Article]:
        kw = (keyword or "").strip()
        if not kw:
            return []

        limit = max(1, min(int(page_size), self.MAX_LIMIT))
        if max_pages is None:
            max_pages = 100

        out: List[Article] = []
        seen_doi: set[str] = set()
        offset = 0
        pages_fetched = 0
        fields = "title,abstract,externalIds,url"

        while True:
            if max_pages is not None and pages_fetched >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            params = {
                "query": kw,
                "limit": limit,
                "offset": offset,
                "fields": fields,
            }
            data = self._get_with_retry(params)
            pages_fetched += 1

            papers = data.get("data") or []
            if not papers:
                break

            for paper in papers:
                title = self._safe_str(paper.get("title"))
                abstract = self._safe_str(paper.get("abstract"))
                if not title or not abstract:
                    continue

                ids = paper.get("externalIds") or {}
                doi = normalize_doi(ids.get("DOI"))
                if doi:
                    if doi in seen_doi:
                        continue
                    seen_doi.add(doi)
                    url = f"https://doi.org/{doi}"
                else:
                    url = self._safe_str(paper.get("url")) or None

                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            offset += limit

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["SemanticScholarSearchAdapter"]
