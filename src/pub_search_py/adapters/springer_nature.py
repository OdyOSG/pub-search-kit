from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class SpringerNatureMetaSearchAdapter(ArticleSearchProvider):
    """Adapter for the Springer Nature Meta v2 API."""

    BASE_URL = "https://api.springernature.com/meta/v2/json"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_s: float = 8.0,
        polite_delay_s: float = 0.0,
        session: Optional[requests.Session] = None,
        user_agent: str = "SpringerNatureMetaSearch/1.0",
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required for Springer Nature Meta API")

        self.api_key = api_key.strip()
        self.timeout_s = float(timeout_s)
        self.polite_delay_s = float(polite_delay_s)
        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _pick_url(record: Dict[str, Any], doi: Optional[str]) -> Optional[str]:
        urls = record.get("url")
        if isinstance(urls, list):
            for entry in urls:
                if isinstance(entry, dict):
                    value = entry.get("value") or entry.get("url")
                    if isinstance(value, str) and value.strip():
                        return value.strip()

        if doi:
            return f"https://doi.org/{doi}"
        return None

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

        p = max(1, min(int(page_size), 100))
        start = 1
        if max_pages is None:
            max_pages = 1

        out: List[Article] = []
        pages_fetched = 0

        while True:
            if pages_fetched >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            params = {
                "q": kw,
                "api_key": self.api_key,
                "p": p,
                "s": start,
            }

            resp = self._session.get(self.BASE_URL, params=params, timeout=self.timeout_s)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

            records = data.get("records") or data.get("record") or []
            if not isinstance(records, list) or not records:
                break

            pages_fetched += 1

            for record in records:
                if not isinstance(record, dict):
                    continue

                title = (record.get("title") or "").strip()
                abstract = (record.get("abstract") or "").strip()
                if not title or not abstract:
                    continue

                doi = normalize_doi(record.get("doi"))
                url = self._pick_url(record, doi)
                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            start += p

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["SpringerNatureMetaSearchAdapter"]
