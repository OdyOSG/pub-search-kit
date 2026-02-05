from .core import Article, ArticleSearchProvider, choose_best_url, normalize_doi
from .adapters import (
    BioRxivSearchAdapter,
    ClinicalTrialsGovSearchAdapter,
    CoreV3SearchAdapter,
    EuropePMCSearchAdapter,
    MedRxivSearchAdapter,
    OpenAlexSearchAdapter,
    PlosSearchAdapter,
    PubMedSearchAdapter,
    SemanticScholarSearchAdapter,
    SpringerNatureMetaSearchAdapter,
)
from .runner import search_across_adapters

__all__ = [
    "Article",
    "ArticleSearchProvider",
    "BioRxivSearchAdapter",
    "ClinicalTrialsGovSearchAdapter",
    "CoreV3SearchAdapter",
    "EuropePMCSearchAdapter",
    "MedRxivSearchAdapter",
    "OpenAlexSearchAdapter",
    "PlosSearchAdapter",
    "PubMedSearchAdapter",
    "SemanticScholarSearchAdapter",
    "SpringerNatureMetaSearchAdapter",
    "choose_best_url",
    "normalize_doi",
    "search_across_adapters",
]
