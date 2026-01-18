# 🔍 Deep Research Tool-Landschaft

Eine umfassende Übersicht über Recherche-Tools für KI-Agenten, basierend auf Best Practices aus professionellen Research-Tools.

---

## Übersicht: Tool-Kategorien

| Tier | Kategorie | Beispiele |
|------|-----------|-----------|
| 1 | Basis-Suche | Tavily, SerpAPI, Brave |
| 2 | News & Aktualität | Google News, NewsAPI, GDELT |
| 3 | Wissenschaft | Semantic Scholar, arXiv, PubMed |
| 4 | Unternehmen | OpenCorporates, North Data, Crunchbase |
| 5 | Patente & IP | Espacenet, DPMA, USPTO |
| 6 | Verwaltung & Recht | TED, EUR-Lex, Gesetze-im-Internet |
| 7 | Statistik & Open Data | Destatis, Eurostat, World Bank |
| 8 | Social Media & Trends | Reddit, Hacker News, Google Trends |
| 9 | Spezial-Datenbanken | Wikipedia, Wikidata, Wolfram Alpha |

---

## Tier 1: Basis-Suche

Allgemeine Websuche - der Fallback für alles.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Tavily** | Für LLMs optimierte Suche, gute Snippets | ✅ | ~$5/1000 | ⭐⭐⭐⭐ |
| **SerpAPI** | Google-Ergebnisse exakt wie Browser | ✅ | ~$50/5000 | ⭐⭐⭐⭐⭐ |
| **Brave Search** | Datenschutz-fokussiert, eigener Index | ✅ | Free Tier | ⭐⭐⭐⭐ |
| **Bing Search** | Microsoft, gut für allgemeine Suche | ✅ | Free Tier | ⭐⭐⭐ |
| **DuckDuckGo** | Privatsphäre, kein Tracking | Inoffiziell | Kostenlos | ⭐⭐⭐ |

### Empfehlung
- **Tavily** als Haupttool (bereits in HayMAS)
- **Brave** als kostenloser Fallback

---

## Tier 2: News & Aktualität

Für aktuelle Ereignisse, Trends, Breaking News.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Google News (gnews)** | Aggregiert News weltweit | Scraping | Kostenlos | ⭐⭐⭐⭐ |
| **NewsAPI.org** | 80.000+ Quellen, strukturiert | ✅ | Free Tier (100/Tag) | ⭐⭐⭐⭐⭐ |
| **Mediastack** | Globale News, viele Sprachen | ✅ | Free Tier | ⭐⭐⭐⭐ |
| **GDELT Project** | Weltnachrichten-DB, Sentiment | BigQuery | Kostenlos | ⭐⭐⭐⭐ |
| **Event Registry** | Events aus News extrahiert | ✅ | Paid | ⭐⭐⭐⭐⭐ |
| **Newscatcher** | News-Aggregation API | ✅ | Paid | ⭐⭐⭐⭐ |

### Code-Beispiel: gnews

```python
from gnews import GNews

def google_news_search(query: str, max_results: int = 10):
    gnews = GNews(language="de", country="DE", period="7d", max_results=max_results)
    results = gnews.get_news(query)
    return [{
        "title": r.get("title"),
        "url": r.get("url"),
        "published": r.get("published date"),
        "source": r.get("publisher", {}).get("title")
    } for r in results]
```

### Empfehlung
- **gnews** für kostenlose News-Suche (bereits im Newsletter-Projekt)
- **NewsAPI.org** für strukturierte, zuverlässige News

---

## Tier 3: Wissenschaft & Forschung

Für wissenschaftliche Fragen, Studien, Paper.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Semantic Scholar** | 200M+ Paper, AI-Zusammenfassungen | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **arXiv** | Preprints (ML, Physik, Math, CS) | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **PubMed/NCBI** | Medizinische Forschung | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **OpenAlex** | 250M+ wissenschaftliche Werke | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Crossref** | DOI-Lookup, Paper-Metadaten | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **CORE** | Open Access Paper | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **Google Scholar** | Via SerpAPI | SerpAPI | Paid | ⭐⭐⭐⭐⭐ |

### Code-Beispiel: Semantic Scholar

```python
import httpx

async def semantic_scholar_search(query: str, limit: int = 10):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,year,authors,citationCount,url"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data.get("data", [])
```

### Empfehlung
- **Semantic Scholar** als Haupttool für Wissenschaft
- **arXiv** speziell für Tech/ML/KI-Themen

---

## Tier 4: Unternehmen & Wirtschaft

Für Firmendaten, Finanzen, Marktanalysen.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **OpenCorporates** | 200M+ Firmen weltweit | ✅ | Free Tier | ⭐⭐⭐⭐ |
| **North Data** | Deutsche Firmen, Verflechtungen | ✅ | €€€ | ⭐⭐⭐⭐⭐ |
| **Handelsregister** | Offizielle DE-Firmendaten | Scraping | Kostenlos | ⭐⭐⭐⭐ |
| **Crunchbase** | Startups, Funding, Investoren | ✅ | $$$ | ⭐⭐⭐⭐⭐ |
| **SEC EDGAR** | US-Börsenberichte | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Bundesanzeiger** | Jahresabschlüsse DE | Scraping | Kostenlos | ⭐⭐⭐⭐ |
| **OpenSanctions** | Sanktionslisten, PEPs | ✅ | Kostenlos | ⭐⭐⭐⭐ |

### Code-Beispiel: OpenCorporates

```python
import httpx

async def company_search(query: str, jurisdiction: str = "de"):
    url = "https://api.opencorporates.com/v0.4/companies/search"
    params = {"q": query, "jurisdiction_code": jurisdiction}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data.get("results", {}).get("companies", [])
```

### Empfehlung
- **OpenCorporates** für internationale Firmensuche (kostenlos)
- **Bundesanzeiger** für deutsche Jahresabschlüsse

---

## Tier 5: Patente & IP

Für Patentrecherchen, Erfindungen, Intellectual Property.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Espacenet (EPO)** | Europäische Patente | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **DPMA** | Deutsche Patente & Marken | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **USPTO** | US-Patente | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Lens.org** | Open Patent Database | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Google Patents** | Globale Suche | Via SerpAPI | Paid | ⭐⭐⭐⭐ |
| **WIPO** | Internationale PCT-Patente | ✅ | Kostenlos | ⭐⭐⭐⭐ |

### Code-Beispiel: Espacenet

```python
import httpx

async def patent_search(query: str, limit: int = 10):
    # Espacenet Open Patent Services (OPS)
    url = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
    params = {"q": f"txt={query}", "Range": f"1-{limit}"}
    headers = {"Accept": "application/json"}
    # Hinweis: Benötigt OAuth2-Token für Production
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()
```

### Empfehlung
- **Lens.org** für einfachen Einstieg (keine Auth nötig)
- **Espacenet OPS** für professionelle Nutzung

---

## Tier 6: Öffentliche Verwaltung & Recht

Für Gesetze, Urteile, Ausschreibungen.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **TED (EU)** | EU-Ausschreibungen | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Bund.de Vergabe** | DE-Ausschreibungen | Scraping | Kostenlos | ⭐⭐⭐⭐ |
| **DTVP** | Deutsches Vergabeportal | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **EUR-Lex** | EU-Gesetze und Urteile | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Gesetze-im-Internet** | Alle DE-Gesetze | Scraping | Kostenlos | ⭐⭐⭐⭐⭐ |
| **OpenLegalData** | DE-Gerichtsurteile | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **dejure.org** | Rechtsprechung, Kommentare | Scraping | Kostenlos | ⭐⭐⭐⭐ |

### Code-Beispiel: TED API

```python
import httpx

async def tender_search(query: str, country: str = "DE"):
    url = "https://ted.europa.eu/api/v3.0/notices/search"
    params = {
        "q": query,
        "fields": "title,buyer,publicationDate,estimatedValue",
        "country": country,
        "size": 20
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()
```

### Empfehlung
- **TED API** für öffentliche Ausschreibungen
- **Gesetze-im-Internet** + **dejure.org** für Rechtsfragen

---

## Tier 7: Statistik & Open Data

Für Zahlen, Fakten, offizielle Statistiken.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Destatis (GENESIS)** | Offizielle DE-Statistiken | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Eurostat** | EU-Statistiken | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **World Bank** | Globale Wirtschaftsdaten | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **OECD Data** | Ländervergleiche | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **GovData.de** | Open Data Portal DE | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **data.gov** | US Open Data | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **Our World in Data** | Visualisierte Statistiken | Download | Kostenlos | ⭐⭐⭐⭐⭐ |

### Code-Beispiel: Destatis GENESIS

```python
import httpx

async def destatis_search(query: str):
    url = "https://www-genesis.destatis.de/genesisWS/rest/2020/find/find"
    params = {
        "username": "GUEST",
        "password": "GUEST",
        "term": query,
        "language": "de"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()
```

### Empfehlung
- **Destatis** für deutsche Statistiken
- **Our World in Data** für globale Trends mit Kontext

---

## Tier 8: Social Media & Trends

Für Meinungen, Diskussionen, Sentiment.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Reddit API** | Diskussionen, Communities | ✅ | Kostenlos (Limits) | ⭐⭐⭐⭐ |
| **Hacker News** | Tech-Community | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Google Trends** | Suchtrends über Zeit | Inoffiziell | Kostenlos | ⭐⭐⭐⭐ |
| **YouTube Data** | Video-Metadaten | ✅ | Kostenlos | ⭐⭐⭐⭐ |
| **Stack Overflow** | Technische Q&A | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Twitter/X** | Echtzeit-Trends | ✅ | $$$ (eingeschränkt) | ⭐⭐⭐ |

### Code-Beispiel: Hacker News

```python
import httpx

async def hackernews_search(query: str, limit: int = 10):
    url = "https://hn.algolia.com/api/v1/search"
    params = {"query": query, "hitsPerPage": limit}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return [{
            "title": hit.get("title"),
            "url": hit.get("url"),
            "points": hit.get("points"),
            "comments": hit.get("num_comments")
        } for hit in data.get("hits", [])]
```

### Empfehlung
- **Hacker News** für Tech-Themen (beste kostenlose API)
- **Reddit** für breite Meinungsbilder

---

## Tier 9: Wissens-Datenbanken

Für strukturiertes Faktenwissen.

| Tool | Beschreibung | API | Kosten | Qualität |
|------|--------------|-----|--------|----------|
| **Wikipedia** | Enzyklopädisches Wissen | ✅ | Kostenlos | ⭐⭐⭐⭐⭐ |
| **Wikidata** | Strukturiertes Weltwissen | SPARQL | Kostenlos | ⭐⭐⭐⭐⭐ |
| **DBpedia** | Wikipedia als Linked Data | SPARQL | Kostenlos | ⭐⭐⭐⭐ |
| **Wolfram Alpha** | Berechnungen, Fakten | ✅ | $ | ⭐⭐⭐⭐⭐ |

### Code-Beispiel: Wikipedia

```python
import httpx

async def wikipedia_search(query: str, limit: int = 5):
    url = "https://de.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data.get("query", {}).get("search", [])

async def wikipedia_summary(title: str):
    url = "https://de.wikipedia.org/api/rest_v1/page/summary/" + title
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Empfehlung
- **Wikipedia** als Fakten-Grundlage für jeden Agenten

---

## Best Practices

### 1. Layered Search Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Orientierung                                       │
│  → Tavily/Google für Überblick                              │
│  → Wikipedia für Grundlagen                                  │
│  → Google Trends für Aktualität                             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: Tiefe                                              │
│  → Spezialisierte DBs je nach Thema                         │
│  → Semantic Scholar für Forschung                           │
│  → News APIs für aktuelle Entwicklungen                     │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: Validierung                                        │
│  → Primärquellen (Gesetze, Patente, Studien)               │
│  → Offizielle Statistiken (Destatis, Eurostat)             │
│  → Cross-Check mit mehreren Quellen                         │
└─────────────────────────────────────────────────────────────┘
```

### 2. Topic-Based Tool Routing

```python
TOOL_ROUTING = {
    "tech_aktuell": ["tavily", "hacker_news", "arxiv", "google_news"],
    "wissenschaft": ["semantic_scholar", "pubmed", "arxiv", "crossref"],
    "unternehmen": ["opencorporates", "northdata", "crunchbase", "news"],
    "recht_de": ["gesetze_im_internet", "dejure", "openlegaldata"],
    "patent": ["espacenet", "dpma", "google_patents", "lens"],
    "vergabe": ["ted_api", "bund_vergabe", "dtvp"],
    "statistik": ["destatis", "eurostat", "worldbank"],
    "meinung": ["reddit", "twitter", "hacker_news", "youtube"],
    "grundlagen": ["wikipedia", "wikidata", "tavily"],
}
```

### 3. Deep Research Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1: Query Expansion                                     │
│  • Kernfrage → 5-10 Sub-Fragen generieren                    │
│  • Synonyme und verwandte Begriffe                           │
│  • Verschiedene Sprachen (DE + EN)                           │
├──────────────────────────────────────────────────────────────┤
│  PHASE 2: Broad Search                                        │
│  • Alle Sub-Fragen parallel suchen                           │
│  • Verschiedene Quellen-Typen abdecken                       │
│  • 50-100 Quellen sammeln                                    │
├──────────────────────────────────────────────────────────────┤
│  PHASE 3: Deep Dive                                           │
│  • Top-Quellen im Volltext lesen                             │
│  • Referenzen verfolgen (Citation Chaining)                  │
│  • Primärquellen identifizieren                              │
├──────────────────────────────────────────────────────────────┤
│  PHASE 4: Synthesis                                           │
│  • Widersprüche identifizieren                               │
│  • Konsens vs. Kontroverse                                   │
│  • Quellenqualität bewerten                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Priorisierte Implementierungs-Roadmap für HayMAS

### Phase 1: Quick Wins (sofort)

| Tool | Aufwand | Impact |
|------|---------|--------|
| Google News (gnews) | 1h | ⭐⭐⭐⭐⭐ |
| Wikipedia API | 1h | ⭐⭐⭐⭐⭐ |
| Hacker News | 30min | ⭐⭐⭐⭐ |

### Phase 2: Wissenschaft & Fakten

| Tool | Aufwand | Impact |
|------|---------|--------|
| Semantic Scholar | 2h | ⭐⭐⭐⭐⭐ |
| arXiv | 1h | ⭐⭐⭐⭐ |

### Phase 3: Business & Recht

| Tool | Aufwand | Impact |
|------|---------|--------|
| OpenCorporates | 2h | ⭐⭐⭐⭐ |
| TED API | 2h | ⭐⭐⭐⭐ |

### Phase 4: Statistik & Deep Research

| Tool | Aufwand | Impact |
|------|---------|--------|
| Destatis | 3h | ⭐⭐⭐⭐ |
| Tool-Routing im Orchestrator | 4h | ⭐⭐⭐⭐⭐ |

---

## Ressourcen & Links

### API-Dokumentationen
- Tavily: https://docs.tavily.com/
- Semantic Scholar: https://api.semanticscholar.org/
- NewsAPI: https://newsapi.org/docs
- OpenCorporates: https://api.opencorporates.com/documentation
- TED: https://ted.europa.eu/TED/misc/helpPage.do?helpPageId=api
- Destatis: https://www-genesis.destatis.de/genesis/online

### Python-Libraries
- `gnews` - Google News Scraping
- `feedparser` - RSS-Feeds
- `scholarly` - Google Scholar (inoffiziell)
- `wikipedia-api` - Wikipedia
- `arxiv` - arXiv API Client

---

*Erstellt: Januar 2026*
*Für: HayMAS Multi-Agent Research System*
