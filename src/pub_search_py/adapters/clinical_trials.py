from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import time

import requests

from ..core import Article, ArticleSearchProvider


class ClinicalTrialsGovSearchAdapter(ArticleSearchProvider):
    """Adapter for the ClinicalTrials.gov v2 studies endpoint."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(
        self,
        *,
        timeout_s: float = 15.0,
        polite_delay_s: float = 0.0,
        strict_match: bool = True,
        session: Optional[requests.Session] = None,
        user_agent: str = "ClinicalTrialsGovArticleSearch/1.0",
        search_mode: str = "term",
    ) -> None:
        self.timeout_s = float(timeout_s)
        self.polite_delay_s = float(polite_delay_s)
        self.strict_match = bool(strict_match)
        self.search_mode = search_mode
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
    def _build_url(nct_id: Optional[str]) -> Optional[str]:
        if not nct_id:
            return None
        value = nct_id.strip()
        if not value:
            return None
        return f"https://clinicaltrials.gov/study/{value}"

    @staticmethod
    def _safe_get(data: Dict[str, Any], path: List[str]) -> Optional[Any]:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    @staticmethod
    def _extract_title(study: Dict[str, Any]) -> str:
        brief = ClinicalTrialsGovSearchAdapter._safe_get(
            study, ["protocolSection", "identificationModule", "briefTitle"]
        )
        if isinstance(brief, str) and brief.strip():
            return brief.strip()

        official = ClinicalTrialsGovSearchAdapter._safe_get(
            study, ["protocolSection", "identificationModule", "officialTitle"]
        )
        if isinstance(official, str) and official.strip():
            return official.strip()

        return ""

    @staticmethod
    def _extract_nct_id(study: Dict[str, Any]) -> Optional[str]:
        value = ClinicalTrialsGovSearchAdapter._safe_get(
            study, ["protocolSection", "identificationModule", "nctId"]
        )
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _extract_summary(study: Dict[str, Any]) -> str:
        summary = ClinicalTrialsGovSearchAdapter._safe_get(
            study, ["protocolSection", "descriptionModule", "briefSummary"]
        )
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        detailed = ClinicalTrialsGovSearchAdapter._safe_get(
            study, ["protocolSection", "descriptionModule", "detailedDescription"]
        )
        if isinstance(detailed, str) and detailed.strip():
            return detailed.strip()
        return ""

    def _request_page(
        self,
        *,
        keyword: str,
        page_size: int,
        page_token: Optional[str],
        count_total: bool,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "format": "json",
            "pageSize": page_size,
            "countTotal": "true" if count_total else "false",
        }

        if self.search_mode == "titles":
            params["query.titles"] = keyword
        else:
            params["query.term"] = keyword

        if page_token:
            params["pageToken"] = page_token

        resp = self._session.get(self.BASE_URL, params=params, timeout=self.timeout_s)
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

        page_size_eff = max(1, min(int(page_size), 250))
        if max_pages is None:
            max_pages = 5

        pattern = None
        if self.strict_match:
            pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)

        out: List[Article] = []
        seen_urls: set[str] = set()
        page_token: Optional[str] = None
        pages = 0

        while True:
            if max_pages is not None and pages >= max_pages:
                break
            if max_items is not None and len(out) >= max_items:
                break

            payload = self._request_page(
                keyword=kw,
                page_size=page_size_eff,
                page_token=page_token,
                count_total=(pages == 0),
            )
            pages += 1

            studies = payload.get("studies") or []
            if not isinstance(studies, list) or not studies:
                break

            for study in studies:
                if not isinstance(study, dict):
                    continue

                title = self._extract_title(study)
                abstract = self._extract_summary(study)
                nct_id = self._extract_nct_id(study)
                url = self._build_url(nct_id)
                if not title or not abstract or not url:
                    continue

                if pattern and not pattern.search(title + "\n" + abstract):
                    continue

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                out.append(Article(title=title, abstract=abstract, doi=None, url=url))

                if max_items is not None and len(out) >= max_items:
                    break

            raw_token = payload.get("nextPageToken")
            page_token = raw_token.strip() if isinstance(raw_token, str) and raw_token.strip() else None
            if not page_token:
                break

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return out[:max_items] if max_items is not None else out


__all__ = ["ClinicalTrialsGovSearchAdapter"]
