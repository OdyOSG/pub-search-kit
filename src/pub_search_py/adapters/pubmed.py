from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import time

import requests

from ..core import Article, ArticleSearchProvider, choose_best_url, normalize_doi


class PubMedSearchAdapter(ArticleSearchProvider):
    """Adapter that fetches articles via the NCBI E-utilities API."""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        *,
        tool: str = "MyMedicalSearchApp",
        email: str = "you@example.com",
        timeout_s: float = 25.0,
        polite_delay_s: float = 0.1,
        batch_size: int = 100,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.tool = tool
        self.email = email
        self.timeout_s = timeout_s
        self.polite_delay_s = polite_delay_s
        self.batch_size = batch_size
        self._session = session or requests.Session()
        self._own_session = session is None
        self._session.headers.update(
            {
                "User-Agent": f"{tool}/1.0 (contact: {email})",
                "Accept": "*/*",
            }
        )

    def close(self) -> None:
        if self._own_session:
            self._session.close()

    @staticmethod
    def _batched(values: List[str], size: int) -> List[List[str]]:
        return [values[i : i + size] for i in range(0, len(values), size)]

    @staticmethod
    def _strip_tags(value: str) -> str:
        return re.sub(r"<.*?>", "", value, flags=re.DOTALL).strip()

    def _parse_pubmed_efetch_xml(self, xml: str) -> List[Article]:
        out: List[Article] = []

        for block in xml.split("<PubmedArticle>")[1:]:
            pmid_match = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
            pmid = pmid_match.group(1) if pmid_match else None
            if not pmid:
                continue

            title_match = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", block, re.DOTALL)
            title = self._strip_tags(title_match.group(1)) if title_match else ""
            if not title:
                continue

            abs_parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", block, re.DOTALL)
            abstract = " ".join(self._strip_tags(part) for part in abs_parts).strip()
            if not abstract:
                continue

            doi_match = re.search(r'<ArticleId\s+IdType="doi">(.*?)</ArticleId>', block, re.DOTALL)
            doi = normalize_doi(self._strip_tags(doi_match.group(1))) if doi_match else None

            pmc_match = re.search(r'<ArticleId\s+IdType="pmc">(PMC\d+)</ArticleId>', block)
            pmc_id = pmc_match.group(1) if pmc_match else None

            pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            pmc_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/" if pmc_id else None
            doi_url = f"https://doi.org/{doi}" if doi else None
            url = choose_best_url([pmc_url, doi_url, pubmed_url])

            out.append(Article(title=title, abstract=abstract, doi=doi, url=url))

        return out

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

        retmax = max_items if max_items is not None else 200
        search_params = {
            "db": "pubmed",
            "term": f"{kw}[Title/Abstract]",
            "retmode": "json",
            "retmax": retmax,
            "tool": self.tool,
            "email": self.email,
        }
        resp = self._session.get(self.ESEARCH_URL, params=search_params, timeout=self.timeout_s)
        resp.raise_for_status()
        pmids: List[str] = resp.json().get("esearchresult", {}).get("idlist", []) or []
        if not pmids:
            return []

        articles: List[Article] = []
        for batch in self._batched(pmids, self.batch_size):
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
                "tool": self.tool,
                "email": self.email,
            }
            batch_resp = self._session.get(self.EFETCH_URL, params=fetch_params, timeout=self.timeout_s)
            batch_resp.raise_for_status()
            xml = batch_resp.text

            for article in self._parse_pubmed_efetch_xml(xml):
                if not article.title or not article.abstract:
                    continue
                articles.append(article)
                if max_items is not None and len(articles) >= max_items:
                    return articles[:max_items]

            if self.polite_delay_s:
                time.sleep(self.polite_delay_s)

        return articles[:max_items] if max_items is not None else articles


__all__ = ["PubMedSearchAdapter"]
