# HayMAS - AI Writing Studio

Ein intelligentes Multi-Agenten-System zur automatischen Generierung hochwertiger Wissensartikel mit dynamischer Recherche-Orchestrierung.

## ✨ Features

### Intelligente Recherche
- **7 Research-Tools**: Tavily, Wikipedia, Google News, Hacker News, Semantic Scholar, arXiv, TED (EU-Ausschreibungen)
- **Dynamische Tool-Auswahl**: Orchestrator empfiehlt passende Tools basierend auf Thementyp
- **Adaptive Recherche-Tiefe**: 2-3 Runden (einfach) → 4-5 (mittel) → 6-8 (komplex)
- **Strukturierte Quellenerfassung**: Jede Quelle mit URL, Titel, Relevanz und Kernfakten

### Smart Editor-Routing
- **Dynamischer Workflow**: Editor entscheidet intelligent zwischen:
  - ✅ **Approved**: Artikel ist fertig
  - ✏️ **Revise**: Writer überarbeitet (Stil/Struktur)
  - 🔍 **Research**: Gezielte Nachrecherche bei Inhaltslücken
- **Automatische Nachrecherche**: Bei Content-Gaps werden spezifische Follow-up-Recherchen durchgeführt

### Multi-Agent System
- **Orchestrator**: Analysiert Thema, plant Recherche, koordiniert Workflow
- **Researcher**: Führt Tool-basierte Recherchen durch, strukturierte JSON-Ausgabe
- **Writer**: Erstellt den Artikel mit Quellenangaben
- **Editor**: Prüft Qualität, identifiziert Lücken, steuert Iteration

### Multi-LLM Support
| Agent | Premium | Budget |
|-------|---------|--------|
| Orchestrator | Claude Opus 4.5 | Claude Sonnet 4.5 |
| Researcher | Claude Sonnet 4.5 | GPT-4o |
| Writer | GPT-5.2 | GPT-5.1 |
| Editor | Claude Sonnet 4.5 | Claude Haiku 4.5 |

### Weitere Features
- **Plan-Editor**: Recherche-Runden und Tools vor Start anpassen
- **Live-Transparenz**: Echtzeit-Updates während der Generierung
- **Session-Logging**: Detaillierte JSON-Logs mit Token-Tracking und Kosten
- **Modernes React-UI**: IDLE → PLANNING → PRODUCING → COMPLETE Workflow

---

## 🚀 Quick Start

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

Erstelle eine `.env` Datei im HayMAS-Verzeichnis:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
# Optional:
GEMINI_API_KEY=...
```

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
│    IDLE     │ →  │  PLANNING   │ →  │  PRODUCING  │ →  │  COMPLETE   │
│  Frage      │    │  Plan       │    │  Agenten    │    │  Artikel    │
│  eingeben   │    │  anpassen   │    │  arbeiten   │    │  anzeigen   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### IDLE
- Kernfrage eingeben
- Beispielfragen verfügbar

### PLANNING
Die KI analysiert automatisch:
- **Thementyp**: tech, business, science, politics, history, culture, general
- **Zeitrelevanz**: current, historical, timeless
- **Komplexität**: simple, medium, complex
- **Geografischer Fokus**: global, regional

Basierend darauf:
- Schlägt passende **Research-Tools** pro Runde vor
- Empfiehlt **Modell-Tiers** pro Agent
- Bestimmt **Anzahl der Recherche-Runden**

Du kannst alles vor dem Start anpassen!

### PRODUCING
- Agenten arbeiten den Plan ab
- Live-Events in der UI:
  - 🔍 Research-Ergebnisse
  - ✍️ Writer-Fortschritt
  - 📝 Editor-Feedback
  - 🎯 **Editor-Verdicts** (approved/revise/research)
  - 🔄 Follow-up-Recherchen bei Bedarf

### COMPLETE
- Artikel mit Quellenverzeichnis
- Download als Markdown
- Session-Log mit Token-Verbrauch und Kosten

---

## 🔧 Research-Tools

| Tool | Beschreibung | Beste für |
|------|--------------|-----------|
| **Tavily** | Web-Suche mit KI-Ranking | Aktuelle Themen, Tech, Business |
| **Wikipedia** | Enzyklopädische Grundlagen | Definitionen, Geschichte, Konzepte |
| **Google News** | Aktuelle Nachrichten | Breaking News, Trends |
| **Hacker News** | Tech-Community Diskussionen | Developer-Perspektiven, Startups |
| **Semantic Scholar** | Wissenschaftliche Paper | Forschung, Studien, Akademisches |
| **arXiv** | Preprints (Science, CS, Math) | KI/ML, Physik, Mathematik |
| **TED** | EU-Ausschreibungen | Öffentlicher Sektor, Vergaben |

### Tool-Diversität
Der Orchestrator sorgt automatisch für Vielfalt:
- Nie das gleiche Tool mehr als 2x hintereinander
- Bei 6+ Runden: Mindestens 5 verschiedene Tools

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                                  │
│   • Themenanalyse → Research-Plan                                    │
│   • Koordiniert Agenten                                              │
│   • Smart Editor-Routing (approved/revise/research)                  │
│   • Follow-up-Recherche bei Content-Gaps                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│    RESEARCHER     │ │      WRITER       │ │      EDITOR       │
│  • Tool-basiert   │ │  • Artikel-Text   │ │  • Qualitätsprüfung│
│  • JSON-Output    │ │  • Quellenangaben │ │  • Issue-Analyse   │
│  • Pro Runde      │ │                   │ │  • Verdict-System  │
└───────────────────┘ └───────────────────┘ └───────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        TOOL REGISTRY                                  │
│   tavily • wikipedia • gnews • hackernews • semantic_scholar         │
│   arxiv • ted • save_markdown                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Projektstruktur

```
HayMAS/
├── api.py                  # FastAPI Backend
├── config.py               # Modell-Konfiguration, Limits
├── session_logger.py       # Session-Logging (JSON)
├── requirements.txt        # Python Dependencies
├── BACKLOG.md              # Geplante Features
│
├── agents/                 # KI-Agenten
│   ├── base_agent.py       # ReAct-Loop, Token-Tracking
│   ├── orchestrator.py     # Themenanalyse, Workflow, Smart Routing
│   ├── researcher.py       # Tool-basierte Recherche, JSON-Output
│   ├── writer.py           # Artikel-Erstellung
│   └── editor.py           # Qualitätsprüfung, Verdict-System
│
├── mcp_server/             # Tool-Server
│   └── tools/
│       ├── registry.py     # Tool-Registry (erweiterbar)
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
│       │   ├── PlanningView.tsx    # Plan-Editor mit Tool-Auswahl
│       │   ├── ProducingView.tsx   # Live-Fortschritt + Verdicts
│       │   └── CompleteView.tsx    # Artikel-Anzeige
│       ├── hooks/useStudio.ts      # State-Management
│       ├── lib/api.ts              # API-Client
│       └── types/index.ts          # TypeScript-Typen
│
├── output/                 # Generierte Artikel (*.md)
└── logs/                   # Session-Logs (*.json)
```

---

## 🔌 API Endpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/` | GET | API-Info |
| `/api/status` | GET | API-Key Status |
| `/api/models` | GET | Verfügbare Modelle |
| `/api/tools` | GET | Alle Research-Tools |
| `/api/tools/{topic_type}` | GET | Tools für Thementyp |
| `/api/analyze` | POST | Themenanalyse → Research-Plan |
| `/api/generate` | POST | Artikel generieren (SSE) |
| `/api/articles` | GET | Liste aller Artikel |
| `/api/articles/{filename}` | GET | Artikel-Inhalt |
| `/api/articles/{filename}/log` | GET | Session-Log |
| `/api/logs` | GET | Alle Session-Logs |

---

## 📊 Session-Logging

Jede Generierung erstellt ein detailliertes JSON-Log:

```json
{
  "session_id": "20260118_180722",
  "question": "...",
  "settings": {
    "research_rounds": 8,
    "use_editor": true,
    "tiers": { "orchestrator": "premium", ... },
    "plan": {
      "topic_type": "tech",
      "complexity": "complex",
      "rounds": [
        { "name": "...", "tool": "wikipedia", ... },
        { "name": "...", "tool": "tavily", ... }
      ]
    }
  },
  "timeline": [
    {
      "agent": "Researcher",
      "action": "research_round_1",
      "tool_calls": ["wikipedia_search"],
      "tokens": { "input": 4560, "output": 919 }
    },
    {
      "agent": "System",
      "action": "event",
      "task": "editor_verdict",
      "details": {
        "verdict": "research",
        "confidence": 0.75,
        "issues_count": 6,
        "has_content_gaps": true
      }
    },
    {
      "agent": "Researcher",
      "action": "followup_research_1",
      "tool_calls": ["tavily_search"]
    }
  ],
  "summary": {
    "total_tokens": { "input": 124116, "output": 42371 },
    "estimated_cost_usd": 1.01,
    "steps_completed": 18
  }
}
```

---

## 🔮 Roadmap

Siehe `BACKLOG.md` für geplante Features:
- Weitere Research-Tools (Destatis, OpenCorporates, Espacenet)
- Konfigurierbare Artikellänge
- Kollaborative Artikel-Erstellung (Epic)
- Verbesserte Budget-Modelle

---

## 🐛 Troubleshooting

### Backend startet nicht
```bash
# Port freigeben
lsof -ti:8000 | xargs kill -9

# Mit PYTHONPATH starten
PYTHONPATH=. python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### "Analyse fehlgeschlagen"
- Backend läuft? `curl http://localhost:8000/api/status`
- API-Keys in `.env` korrekt?

### Rate Limit (429)
- Wechsle betroffene Agenten auf "Budget" Modelle in den Settings

---

## 📄 Lizenz

MIT
