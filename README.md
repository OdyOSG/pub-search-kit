pub-search-py
=============

`pub-search-py` is a lightweight Python library that exposes a unified protocol for searching biomedical and scholarly literature across multiple public APIs. Every adapter implements the same `ArticleSearchProvider` interface, so you can swap providers (or aggregate them) while keeping downstream code identical.

Features
--------

- **Consistent protocol** – each adapter returns the same `Article` dataclass (`title`, `abstract`, `doi`, `url`).
- **Plug-and-play adapters** – pick only the providers you need, or iterate across several.
- **Polite defaults** – sane timeouts, optional polite delays, and local filtering to avoid irrelevant hits.
- **Requests-based** – no heavy dependencies other than `requests`.

Included adapters
-----------------

| Module | Class | API |
| --- | --- | --- |
| `pub_search_py.adapters.europe_pmc` | `EuropePMCSearchAdapter` | Europe PMC REST |
| `pub_search_py.adapters.pubmed` | `PubMedSearchAdapter` | NCBI E-utilities (esearch/efetch) |
| `pub_search_py.adapters.plos` | `PlosSearchAdapter` | PLOS Search API |
| `pub_search_py.adapters.medrxiv` | `MedRxivSearchAdapter` | medRxiv endpoint on api.biorxiv.org |
| `pub_search_py.adapters.biorxiv` | `BioRxivSearchAdapter` | bioRxiv endpoint on api.biorxiv.org |
| `pub_search_py.adapters.openalex` | `OpenAlexSearchAdapter` | OpenAlex Works |
| `pub_search_py.adapters.core_v3` | `CoreV3SearchAdapter` | CORE v3 works (requires API key) |
| `pub_search_py.adapters.semantic_scholar` | `SemanticScholarSearchAdapter` | Semantic Scholar Graph |
| `pub_search_py.adapters.clinical_trials` | `ClinicalTrialsGovSearchAdapter` | ClinicalTrials.gov API v2 |
| `pub_search_py.adapters.springer_nature` | `SpringerNatureMetaSearchAdapter` | Springer Nature Meta v2 (requires API key) |

Installation
------------

The project uses `uv` for packaging, but you can install it into any Python ≥3.12 environment directly from GitHub:

```bash
pip install "git+https://github.com/odyosg/pub-search-py.git"
```

If you prefer `uv`, clone the repository and run:

```bash
git clone https://github.com/odyosg/pub-search-py.git
cd pub-search-py
uv sync
```

Usage
-----

```python
from pub_search_py import ArticleSearchProvider, EuropePMCSearchAdapter

def dump_headlines(searcher: ArticleSearchProvider, keyword: str) -> None:
    articles = searcher.search_by_keyword(keyword, max_items=5)
    for idx, article in enumerate(articles, 1):
        print(f"{idx}. {article.title} ({article.url})")

adapter = EuropePMCSearchAdapter(user_agent="MyCoolApp/0.1 (contact: you@example.com)")
try:
    dump_headlines(adapter, "ibuprofen")
finally:
    adapter.close()
```

Parallel search across adapters:

```python
from pub_search_py import (
    EuropePMCSearchAdapter,
    PubMedSearchAdapter,
    search_across_adapters,
)

adapters = [
    EuropePMCSearchAdapter(user_agent="MyApp/0.1"),
    PubMedSearchAdapter(tool="MyApp", email="me@example.com"),
]

results = search_across_adapters(adapters, "ibuprofen", max_items=5)
for adapter_name, articles in results.items():
    print(adapter_name, len(articles))
```

Provider notes
--------------

- **Rate limits** – many APIs expect a descriptive `User-Agent`, and some (Semantic Scholar, OpenAlex, CORE, Springer Nature) recommend `mailto` or API-key parameters. Review each adapter docstring for the knobs you can tweak.
- **API keys** – CORE v3 and Springer Nature Meta *require* keys; Semantic Scholar and OpenAlex keys boost limits but are optional.
- **Polite delays** – defaults keep interactive usage civil. Increase `polite_delay_s` for batch jobs.

Development
-----------

```bash
git clone https://github.com/odyosg/pub-search-py.git
cd pub-search-py
uv sync            # install dev deps
PYTHONPATH=src pytest  # add your tests
```

Contributions are welcome—open an issue or PR with adapters for additional data sources or improvements to the shared protocol.
