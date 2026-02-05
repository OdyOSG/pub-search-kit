from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class MedRxivSearchAdapter(ArticleSearchProvider):
    """Adapter for the medRxiv endpoint exposed by api.biorxiv.org."""

    BASE_URL = "https://api.biorxiv.org/details/medrxiv"
    API_PAGE_CAP = 100

    def __init__(
        self,
        *,
        days_back: int = 14,
        timeout_s: float = 6.0,
        polite_delay_s: float = 0.0,
        session: Optional[requests.Session] = None,
        user_agent: str = "MedRxivArticleSearch/1.0",
    ) -> None:
        self.days_back = int(days_back)
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

        kw_lower = kw.lower()
        today = date.today()
        start = today - timedelta(days=self.days_back)
        start_s, end_s = start.isoformat(), today.isoformat()

        if max_pages is None:
            max_pages = 20

        return_cap = max(1, int(page_size))

        out: List[Article] = []
        cursor = 0

        for _ in range(max_pages):
            if max_items is not None and len(out) >= max_items:
                break

            url = f"{self.BASE_URL}/{start_s}/{end_s}/{cursor}/json"
            resp = self._session.get(url, timeout=self.timeout_s)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

            items = data.get("collection") or []
            if not items:
                break

            for entry in items:
                title = (entry.get("title") or "").strip()
                abstract = (entry.get("abstract") or "").strip()
                if not title or not abstract:
                    continue

                haystack = (title + "\n" + abstract).lower()
                if kw_lower not in haystack:
                    continue

                doi = normalize_doi(entry.get("doi"))
                version = (entry.get("version") or "").strip() or None
                url = f"https://www.medrxiv.org/content/{doi}v{version}" if doi and version else None

                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    return out[:max_items]
                if max_items is None and len(out) >= return_cap:
                    return out

            cursor += self.API_PAGE_CAP

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["MedRxivSearchAdapter"]
