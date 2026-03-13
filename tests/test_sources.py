from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from paper_alert.sources.arxiv import fetch_arxiv
from paper_alert.sources.crossref import fetch_crossref
from paper_alert.sources.pubmed import fetch_pubmed
from paper_alert.sources.semanticscholar import fetch_semantic_scholar


def test_fetch_arxiv_matches_keyword_in_summary(monkeypatch):
    payload = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <title>Generic neuromodulation study</title>
    <summary>Temporal interference stimulation improves targeting.</summary>
    <published>2024-06-01T00:00:00Z</published>
    <link rel="alternate" href="https://arxiv.org/abs/1234.5678" />
  </entry>
</feed>
"""

    monkeypatch.setattr("paper_alert.sources.arxiv.fetch_text", lambda url: payload)

    papers = fetch_arxiv(("temporal interference",))

    assert len(papers) == 1
    assert papers[0].title == "Generic neuromodulation study"


def test_fetch_pubmed_does_not_drop_results_based_on_title_only(monkeypatch):
    def fake_fetch_json(url):
        if "esearch.fcgi" in url:
            return {"esearchresult": {"idlist": ["42"]}}
        return {
            "result": {
                "uids": ["42"],
                "42": {
                    "title": "Focused stimulation in deep targets",
                    "sortpubdate": "2024/06/01 00:00",
                },
            }
        }

    monkeypatch.setattr("paper_alert.sources.pubmed.fetch_json", fake_fetch_json)
    monkeypatch.setattr("paper_alert.sources.pubmed.polite_delay", lambda: None)

    papers = fetch_pubmed(("temporal interference",))

    assert len(papers) == 1
    assert papers[0].identifier == "42"


def test_fetch_crossref_matches_keyword_in_abstract(monkeypatch):
    monkeypatch.setattr(
        "paper_alert.sources.crossref.fetch_json",
        lambda url: {
            "message": {
                "items": [
                    {
                        "title": ["Broadband field shaping"],
                        "abstract": "A temporal interference paradigm for stimulation.",
                        "DOI": "10.1000/example",
                        "URL": "https://doi.org/10.1000/example",
                        "issued": {"date-parts": [[2024, 5, 15]]},
                    }
                ]
            }
        },
    )

    papers = fetch_crossref(("temporal interference",))

    assert len(papers) == 1
    assert papers[0].identifier == "10.1000/example"


def test_fetch_semantic_scholar_requests_stable_identifier_and_abstract(monkeypatch):
    def fake_fetch_json(url, headers=None):
        parsed = parse_qs(urlparse(url).query)
        assert headers == {"x-api-key": "secret"}
        assert "paperId" in parsed["fields"][0]
        assert "abstract" in parsed["fields"][0]
        return {
            "data": [
                {
                    "title": "Computational modeling study",
                    "abstract": "Temporal interference enables selective modulation.",
                    "publicationDate": "2024-05-01",
                    "externalIds": {"DOI": "10.2000/semantic"},
                }
            ]
        }

    monkeypatch.setattr(
        "paper_alert.sources.semanticscholar.fetch_json",
        fake_fetch_json,
    )

    papers = fetch_semantic_scholar(
        ("temporal interference",),
        api_key="secret",
    )

    assert len(papers) == 1
    assert papers[0].identifier == "10.2000/semantic"
