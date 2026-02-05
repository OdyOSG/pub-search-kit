from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class EuropePMCSearchAdapter(ArticleSearchProvider):
    """Adapter for the Europe PMC REST API."""

    SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(
        self,
        *,
        timeout_s: float = 25.0,
        polite_delay_s: float = 0.1,
        session: Optional[requests.Session] = None,
        user_agent: str = "EPMCAbstractFetcher/1.0 (contact: you@example.com)",
    ) -> None:
        self.timeout_s = timeout_s
        self.polite_delay_s = polite_delay_s
        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _canonical_url(item: Dict[str, Any]) -> Optional[str]:
        source = item.get("source")
        rec_id = item.get("id")
        if source and rec_id:
            return f"https://europepmc.org/article/{source}/{rec_id}"
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

        kw_escaped = kw.replace('"', r"\"")
        query = f'(TITLE:"{kw_escaped}" OR ABSTRACT:"{kw_escaped}")'

        cursor_mark = "*"
        pages = 0
        out: List[Article] = []

        while True:
            if max_pages is not None and pages >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            params = {
                "query": query,
                "resultType": "core",
                "format": "json",
                "pageSize": page_size,
                "cursorMark": cursor_mark,
            }
            resp = self._session.get(self.SEARCH_URL, params=params, timeout=self.timeout_s)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

            results = (data.get("resultList") or {}).get("result") or []
            if not results:
                break

            for entry in results:
                title = (entry.get("title") or "").strip()
                abstract = (entry.get("abstractText") or "").strip()
                if not title or not abstract:
                    continue

                doi = normalize_doi(entry.get("doi"))
                url = self._canonical_url(entry)

                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            pages += 1
            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["EuropePMCSearchAdapter"]
