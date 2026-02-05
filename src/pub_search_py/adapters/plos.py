from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class PlosSearchAdapter(ArticleSearchProvider):
    """Adapter for the PLOS Search API (https://api.plos.org/)."""

    SEARCH_URL = "https://api.plos.org/search"

    def __init__(
        self,
        *,
        polite_delay_s: float = 0.1,
        timeout_s: float = 20.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.polite_delay_s = polite_delay_s
        self.timeout_s = timeout_s
        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "User-Agent": "PLOSArticleSearch/1.0",
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    def search_by_keyword(
        self,
        keyword: str,
        *,
        page_size: int = 25,
        max_items: Optional[int] = 200,
        max_pages: Optional[int] = None,
    ) -> List[Article]:
        if not keyword or not keyword.strip():
            return []

        query = f'(title:"{keyword}" OR abstract:"{keyword}")'
        params = {
            "q": query,
            "fl": "title,abstract,doi,id",
            "wt": "json",
            "rows": max_items if max_items is not None else page_size,
        }

        resp = self._session.get(self.SEARCH_URL, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        payload: Dict[str, Any] = resp.json()

        docs = payload.get("response", {}).get("docs", []) or []
        out: List[Article] = []

        for doc in docs:
            title_val = doc.get("title", "")
            abstract_val = doc.get("abstract", "")
            doi_val = doc.get("doi", "")

            if not title_val or not abstract_val:
                continue

            title = title_val[0].strip() if isinstance(title_val, list) else str(title_val).strip()
            abstract = (
                abstract_val[0].strip() if isinstance(abstract_val, list) else str(abstract_val).strip()
            )
            doi = normalize_doi(doi_val[0] if isinstance(doi_val, list) else doi_val)

            url = f"https://journals.plos.org/plosone/article?id={doi}" if doi else None

            out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

            if max_items is not None and len(out) >= max_items:
                break

        if self.polite_delay_s:
            time.sleep(self.polite_delay_s)

        return out


__all__ = ["PlosSearchAdapter"]
