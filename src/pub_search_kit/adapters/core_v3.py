from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class CoreV3SearchAdapter(ArticleSearchProvider):
    """Adapter for the CORE v3 works endpoint."""

    BASE_URL = "https://api.core.ac.uk/v3"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_s: float = 15.0,
        polite_delay_s: float = 0.0,
        strict_match: bool = True,
        session: Optional[requests.Session] = None,
        user_agent: str = "COREArticleSearch/1.0",
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("CORE api_key is required.")

        self.api_key = api_key.strip()
        self.timeout_s = float(timeout_s)
        self.polite_delay_s = float(polite_delay_s)
        self.strict_match = bool(strict_match)

        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
                "Authorization": f"Bearer {self.api_key}",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _pick_url(item: Dict[str, Any], doi: Optional[str]) -> Optional[str]:
        download = item.get("downloadUrl")
        if isinstance(download, str) and download.strip():
            return download.strip()

        urls = item.get("urls")
        if isinstance(urls, list):
            for candidate in urls:
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        if doi:
            return f"https://doi.org/{doi}"

        work_id = item.get("id")
        if isinstance(work_id, (int, str)) and str(work_id).strip():
            return f"https://core.ac.uk/works/{str(work_id).strip()}"
        return None

    def _request_page(self, *, q: str, limit: int, offset: int) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/search/works"
        params = {"q": q, "limit": limit, "offset": offset}
        resp = self._session.get(url, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

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

        limit = max(1, min(int(page_size), 100))
        if max_pages is None:
            max_pages = 5

        pattern = None
        if self.strict_match:
            pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)

        out: List[Article] = []
        seen_doi: set[str] = set()
        offset = 0
        pages = 0

        while True:
            if max_pages is not None and pages >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            data = self._request_page(q=kw, limit=limit, offset=offset)
            pages += 1

            results = data.get("results") or []
            if not isinstance(results, list) or not results:
                break

            for item in results:
                if not isinstance(item, dict):
                    continue

                title_val = item.get("title")
                title = title_val.strip() if isinstance(title_val, str) else ""
                abstract_val = item.get("abstract")
                abstract = abstract_val.strip() if isinstance(abstract_val, str) else ""
                if not title or not abstract:
                    continue

                if pattern and not pattern.search(title + "\n" + abstract):
                    continue

                doi = normalize_doi(item.get("doi"))
                if doi:
                    if doi in seen_doi:
                        continue
                    seen_doi.add(doi)

                url = self._pick_url(item, doi)
                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            offset += limit

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["CoreV3SearchAdapter"]
