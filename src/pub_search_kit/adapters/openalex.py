from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import time

import requests

from ..core import Article, ArticleSearchProvider, normalize_doi


class OpenAlexSearchAdapter(ArticleSearchProvider):
    """Adapter for the OpenAlex Work search endpoint."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        timeout_s: float = 10.0,
        polite_delay_s: float = 0.0,
        strict_match: bool = True,
        mailto: Optional[str] = None,
        session: Optional[requests.Session] = None,
        user_agent: str = "OpenAlexArticleSearch/1.0",
    ) -> None:
        self.timeout_s = float(timeout_s)
        self.polite_delay_s = float(polite_delay_s)
        self.strict_match = bool(strict_match)
        self.mailto = mailto
        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _decode_abstract(abstract_inverted_index: Optional[Dict[str, Any]]) -> str:
        if not isinstance(abstract_inverted_index, dict) or not abstract_inverted_index:
            return ""

        max_pos = -1
        for positions in abstract_inverted_index.values():
            if isinstance(positions, list):
                for pos in positions:
                    if isinstance(pos, int) and pos > max_pos:
                        max_pos = pos

        if max_pos < 0:
            return ""

        words = [""] * (max_pos + 1)
        for token, positions in abstract_inverted_index.items():
            if not isinstance(token, str) or not isinstance(positions, list):
                continue
            for pos in positions:
                if isinstance(pos, int) and 0 <= pos <= max_pos:
                    words[pos] = token

        return " ".join(part for part in words if part).strip()

    @staticmethod
    def _pick_url(work: Dict[str, Any], doi: Optional[str]) -> Optional[str]:
        location = work.get("primary_location") or {}
        landing = location.get("landing_page_url")
        if isinstance(landing, str) and landing.strip():
            return landing.strip()

        if doi:
            return f"https://doi.org/{doi}"

        work_id = work.get("id")
        if isinstance(work_id, str) and work_id.strip():
            return work_id.strip()
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

        per_page = max(1, min(int(page_size), 200))
        if max_pages is None:
            max_pages = 1

        pattern = None
        if self.strict_match:
            pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)

        out: List[Article] = []
        seen_doi: set[str] = set()
        page = 1
        pages_fetched = 0

        while True:
            if max_pages is not None and pages_fetched >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            params: Dict[str, Any] = {
                "search": kw,
                "per_page": per_page,
                "page": page,
            }
            if self.mailto:
                params["mailto"] = self.mailto

            resp = self._session.get(self.BASE_URL, params=params, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results") or []
            if not isinstance(results, list) or not results:
                break

            pages_fetched += 1

            for work in results:
                if not isinstance(work, dict):
                    continue

                title_val = work.get("title")
                title = title_val.strip() if isinstance(title_val, str) else ""
                abstract = self._decode_abstract(work.get("abstract_inverted_index"))
                if not title or not abstract:
                    continue

                if pattern and not pattern.search(title + "\n" + abstract):
                    continue

                doi = normalize_doi(work.get("doi"))
                if doi:
                    if doi in seen_doi:
                        continue
                    seen_doi.add(doi)

                url = self._pick_url(work, doi)
                out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            page += 1

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["OpenAlexSearchAdapter"]
