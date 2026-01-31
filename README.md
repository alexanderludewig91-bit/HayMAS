# HayMAS - AI Writing Studio

Ein intelligentes Multi-Agenten-System zur automatischen Generierung wissenschaftlicher Fachartikel mit **Evidence-Gated Workflow** und dynamischer Quellenrecherche.

## ✨ Features

### Evidence-Gated Workflow (8-Phasen-System)
Der Kern von HayMAS: Ein wissenschaftlicher Ansatz zur Artikelgenerierung, bei dem **Behauptungen (Claims) zuerst definiert und dann mit Quellen belegt werden**.

| Phase | Agent | Aufgabe |
|-------|-------|---------|
| 1-2 | **ClaimMiner** | Analysiert Frage, erstellt ClaimRegister mit A/B/C-Evidenzklassen |
| 3-4 | **TargetedRetriever** | Gezielte Recherche für B/C-Claims mit Retrieval-Tickets |
| 5 | **EvidenceRater** | Bewertet Quellen nach Autorität und Unabhängigkeit |
| 6 | **ClaimBoundedWriter** | Schreibt Artikel strikt basierend auf belegten Claims |
| 7 | **EditorialReviewer** | Prüft Qualität, Halluzinationen, Quellenreferenzierung |
| 8 | **BibliographyBuilder** | Erstellt konsistentes Literaturverzeichnis |

### Claim-Evidenzklassen
- **A-Claims**: Stabiles Allgemeinwissen (keine Quelle nötig)
- **B-Claims**: Benötigen 1 gute Quelle
- **C-Claims**: Benötigen 2+ unabhängige Quellen (für Zahlen, aktuelle Fakten!)

### Prompt Refiner
Intelligenter Dialog vor der Artikelgenerierung:
- **Format wählen**: Übersicht (3-5 S.) | Fachartikel (8-10 S.) | Expertenbericht (10-15 S.) | Deep-Dive (15-20 S.)
- **Zielgruppe wählen**: Fachexperten | Management | Einsteiger
- Automatische Prompt-Optimierung für bessere Ergebnisse

### Multi-LLM Support

| Agent | Premium | Budget |
|-------|---------|--------|
| ClaimMiner/Orchestrator | Claude Opus 4.5 | Claude Sonnet 4.5 |
| Researcher | Claude Sonnet 4.5 | GPT-4o |
| Writer | GPT-5.2 | GPT-5.1 |
| Editor | Claude Sonnet 4.5 | Claude Haiku 4.5 |
| Verifier | Gemini 3 Pro | Gemini 2.5 Flash |

### 7 Research-Tools
| Tool | Beschreibung | Beste für |
|------|--------------|-----------|
| **Tavily** | Web-Suche mit KI-Ranking | Aktuelle Themen, Tech, Business |
| **Wikipedia** | Enzyklopädische Grundlagen | Definitionen, Geschichte, Konzepte |
| **Google News** | Aktuelle Nachrichten | Breaking News, Trends |
| **Hacker News** | Tech-Community Diskussionen | Developer-Perspektiven, Startups |
| **Semantic Scholar** | Wissenschaftliche Paper | Forschung, Studien, Akademisches |
| **arXiv** | Preprints (Science, CS, Math) | KI/ML, Physik, Mathematik |
| **TED** | EU-Ausschreibungen | Öffentlicher Sektor, Vergaben |

### Qualitätssicherung
- **Halluzinations-Check**: Editor erkennt unbelegte Faktenbehauptungen
- **Kritische Abbruchbedingungen**: Bei 0 Claims oder 0 Quellen wird abgebrochen
- **Revisionsschleife**: Max. 2 Überarbeitungsrunden mit gezielten Korrekturen
- **Quellen-Sanitization**: Ungültige Referenzen werden automatisch entfernt

---

## 🚀 Quick Start

### Option A: Docker (empfohlen)

Die einfachste Installation via Docker:

**1. Image laden** (von [GitHub Release](https://github.com/alexanderludewig91-bit/HayMAS/releases)):
```bash
docker load -i haymas-docker.tar.gz
```

**2. Container starten:**
```bash
docker run -d \
  --name haymas \
  -p 8000:8000 \
  -v haymas-data:/app/data \
  -v haymas-output:/app/output \
  -v haymas-logs:/app/logs \
  haymas:latest
```

**3. Öffnen:** http://localhost:8000

**4. API-Keys konfigurieren:** Klicke auf das Zahnrad-Icon (⚙️) in der Anwendung.

---

### Option B: Lokale Entwicklung

### 1. Backend Setup

```bash
cd HayMAS

# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. API-Keys konfigurieren

**Option A: Im Frontend (empfohlen)**

Klicke auf das Zahnrad-Icon (⚙️) oben rechts in der Anwendung. Dort können alle API-Keys direkt eingegeben und gespeichert werden. Die Keys werden persistent in `data/config.json` gespeichert.

**Option B: Via .env Datei**

Erstelle eine `.env` Datei im HayMAS-Verzeichnis:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
# Optional:
GEMINI_API_KEY=...
```

> **Hinweis:** Im Frontend eingegebene Keys überschreiben die .env Werte.

### 4. Anwendung starten

**Terminal 1 – Backend:**
```bash
source venv/bin/activate
PYTHONPATH=. python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 – Frontend:**
```bash
cd frontend
npm run dev
```

| URL | Beschreibung |
|-----|--------------|
| http://localhost:5173 | **Frontend** (hier arbeiten!) |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | Swagger API-Dokumentation |

---

## 📋 Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    IDLE     │ →  │   REFINE    │ →  │  PRODUCING  │ →  │  COMPLETE   │
│  Frage      │    │  Format &   │    │  8-Phasen   │    │  Artikel    │
│  eingeben   │    │  Zielgruppe │    │  Workflow   │    │  anzeigen   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### IDLE
- Kernfrage eingeben
- Beispielfragen verfügbar

### REFINE (Prompt Optimizer)
Wähle vor dem Start:
- **Format**: Übersicht | Fachartikel | Expertenbericht | Deep-Dive
- **Zielgruppe**: Fachexperten | Management | Einsteiger
- Der Prompt wird automatisch für optimale Ergebnisse angepasst

### PRODUCING
Der Evidence-Gated Workflow läuft ab:
1. ⛏️ **ClaimMiner** analysiert Frage und erstellt Claims
2. 🔍 **Retriever** recherchiert für B/C-Claims
3. ⚖️ **Rater** bewertet Quellenqualität
4. ✍️ **Writer** schreibt den Artikel
5. 📋 **Editor** prüft und gibt Feedback
6. ✏️ **Reviser** überarbeitet bei Bedarf (max. 2x)
7. 📚 **Bibliography** erstellt Quellenverzeichnis

### COMPLETE
- Artikel mit vollständigem Quellenverzeichnis
- Download als Markdown oder PDF
- Session-Log mit Token-Verbrauch und Kosten

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EVIDENCE-GATED ORCHESTRATOR                           │
│   • 8-Phasen-Workflow                                                   │
│   • Dynamische Modellauswahl (Premium/Budget)                           │
│   • Kritische Abbruchbedingungen                                        │
│   • Revisionsschleife mit Halluzinations-Check                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────┬───────────┬───────┴───────┬───────────┬───────────┐
    ▼           ▼           ▼               ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐
│ Claim   │ │Targeted │ │Evidence │ │ClaimBounded │ │Editorial│ │Bibliogr.│
│ Miner   │ │Retriever│ │ Rater   │ │  Writer     │ │Reviewer │ │ Builder │
│         │ │         │ │         │ │             │ │         │ │         │
│A/B/C    │ │MCP Tools│ │Autorität│ │Quellen-     │ │Halluz.- │ │Konsist. │
│Claims   │ │Recherche│ │Ranking  │ │gebunden     │ │Check    │ │Referenz.│
└─────────┘ └─────────┘ └─────────┘ └─────────────┘ └─────────┘ └─────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TOOL REGISTRY (MCP)                             │
│   tavily • wikipedia • gnews • hackernews • semantic_scholar            │
│   arxiv • ted • save_markdown                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Projektstruktur

```
HayMAS/
├── api.py                  # FastAPI Backend mit SSE
├── config.py               # Modell-Konfiguration, Tier-System, API-Key-Verwaltung
├── session_logger.py       # Detailliertes Session-Logging (JSON)
├── requirements.txt        # Python Dependencies
├── BACKLOG.md              # Geplante Features
├── Dockerfile              # Docker-Image Definition
├── docker-compose.yml      # Docker Compose Konfiguration
├── .dockerignore           # Docker Build Excludes
├── env.example             # Beispiel für .env Datei
│
├── evidence_gated/         # 🆕 Evidence-Gated System
│   ├── orchestrator.py     # 8-Phasen-Workflow, FORMAT_SPECS
│   ├── models.py           # ClaimRegister, QuestionBrief, etc.
│   └── agents/
│       ├── claim_miner.py
│       ├── targeted_retriever.py
│       ├── evidence_rater.py
│       ├── claim_bounded_writer.py
│       ├── editorial_reviewer.py
│       └── final_verifier.py
│
├── agents/                 # Legacy-Agenten (Standard-Flow)
│   ├── base_agent.py       # ReAct-Loop, Token-Tracking
│   ├── orchestrator.py     # Alter Flow (Research-Runden)
│   ├── researcher.py
│   ├── writer.py
│   ├── editor.py
│   └── prompt_optimizer.py # 🆕 Prompt Refiner Backend
│
├── mcp_server/             # Tool-Server
│   └── tools/
│       ├── registry.py     # Tool-Registry
│       ├── tavily_search.py
│       ├── wikipedia_tool.py
│       ├── gnews_tool.py
│       ├── hackernews_tool.py
│       ├── semantic_scholar_tool.py
│       ├── arxiv_tool.py
│       ├── ted_tool.py
│       └── file_tools.py
│
├── frontend/               # React Frontend
│   └── src/
│       ├── components/
│       │   ├── Studio.tsx          # Haupt-Container
│       │   ├── IdleView.tsx        # Frage-Eingabe
│       │   ├── PromptRefiner.tsx   # 🆕 Format/Audience Auswahl
│       │   ├── ProducingView.tsx   # Live-Fortschritt
│       │   ├── CompleteView.tsx    # Artikel-Anzeige
│       │   ├── ArchiveDrawer.tsx   # Artikel-Archiv
│       │   └── SettingsDrawer.tsx  # API-Keys & Tier-Einstellungen
│       ├── hooks/useStudio.ts
│       ├── lib/api.ts
│       └── types/index.ts
│
├── templates/
│   └── pdf_style.css       # PDF-Styling für Export
│
├── output/                 # Generierte Artikel (*.md)
└── logs/                   # Session-Logs (*.json)
```

---

## 📊 Artikel-Formate

| Format | Seiten | Wörter | Claims min. | C-Claims min. |
|--------|--------|--------|-------------|---------------|
| **overview** | 3-5 | 1200-1800 | 10 | 3 |
| **article** | 8-10 | 2000-3000 | 15 | 5 |
| **report** | 10-15 | 3000-4500 | 20 | 7 |
| **deep_dive** | 15-20 | 5000-7000 | 30 | 10 |

---

## 🔌 API Endpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/` | GET | API-Info |
| `/api/status` | GET | API-Key Status |
| `/api/models` | GET | Verfügbare Modelle |
| `/api/tools` | GET | Alle Research-Tools |
| `/api/refine-prompt` | POST | 🆕 Prompt optimieren |
| `/api/analyze` | POST | Themenanalyse (Legacy) |
| `/api/generate` | POST | Artikel generieren (SSE) |
| `/api/articles` | GET | Liste aller Artikel |
| `/api/articles/{filename}` | GET | Artikel-Inhalt |
| `/api/articles/{filename}/pdf` | GET | Artikel als PDF |
| `/api/articles/{filename}/log` | GET | Session-Log |
| `/api/logs` | GET | Alle Session-Logs |

---

## 📊 Session-Logging

Jede Generierung erstellt ein detailliertes JSON-Log:

```json
{
  "session_id": "20260126_214451",
  "question": "...",
  "settings": {
    "mode": "evidence_gated",
    "tiers": { "orchestrator": "budget", "writer": "budget", ... },
    "format": "overview",
    "target_pages": 4
  },
  "timeline": [
    {
      "agent": "ClaimMiner",
      "model": "claude-sonnet-4-5",
      "action": "claim_mining",
      "tokens": { "input": 976, "output": 4107 },
      "details": {
        "claims_count": 13,
        "a_claims": 3, "b_claims": 2, "c_claims": 8
      }
    },
    {
      "agent": "TargetedRetriever",
      "action": "targeted_retrieval",
      "tool_calls": ["tavily", "gnews"],
      "details": {
        "claims_processed": 10,
        "total_sources": 22
      }
    },
    {
      "agent": "EditorialReviewer",
      "action": "editorial_review",
      "details": {
        "verdict": "revise",
        "issues_count": 6,
        "issues": [...]
      }
    }
  ],
  "summary": {
    "total_tokens": { "input": 26502, "output": 14050 },
    "estimated_cost_usd": 0.29,
    "steps_completed": 8
  }
}
```

---

## 🔮 Roadmap

Siehe `BACKLOG.md` für geplante Features:
- Gemini Deep Research Integration
- Weitere Research-Tools (Destatis, OpenCorporates)
- Kollaborative Artikel-Erstellung
- Verbesserte Budget-Modelle

---

## 🐳 Docker

### Container-Management

```bash
# Container starten
docker start haymas

# Container stoppen
docker stop haymas

# Logs anzeigen
docker logs haymas

# In Container-Shell
docker exec -it haymas /bin/bash
```

### Daten-Volumes

| Volume | Inhalt |
|--------|--------|
| `haymas-data` | API-Keys (config.json) |
| `haymas-output` | Generierte Artikel (*.md) |
| `haymas-logs` | Session-Logs (*.json) |

### Eigenes Image bauen

```bash
# Image bauen
docker build -t haymas:latest .

# Oder mit docker-compose
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
# Port freigeben
lsof -ti:8000 | xargs kill -9

# Mit PYTHONPATH starten
PYTHONPATH=. python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### "0 Claims" Fehler
Der ClaimMiner konnte keine Claims extrahieren. Mögliche Ursachen:
- Frage zu vage oder zu kurz
- API Rate Limit erreicht
- Versuche es mit einem anderen Prompt

### Rate Limit (429)
- Wechsle betroffene Agenten auf "Budget" Modelle in den Settings
- Warte einige Minuten und versuche es erneut

### Artikel zu kurz
- Der Editor prüft die Mindestlänge
- Bei zu kurzen Revisionen wird das Original behalten
- Wähle ein größeres Format (z.B. "report" statt "overview")

---

## 📄 Lizenz

MIT
