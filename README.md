# HayMAS - AI Writing Studio

Ein Multi-Agenten-System, das aus einer Kernfrage automatisch hochwertige Wissensartikel generiert.

## Features

- **Intelligente Themenanalyse**: KI analysiert das Thema und schlägt optimale Recherche-Strategie vor
- **Plan-Editor**: Recherche-Runden vor dem Start anpassen, aktivieren/deaktivieren
- **Multi-Agent System**: Orchestrator, Researcher, Writer und Editor arbeiten zusammen
- **Multi-LLM**: Unterstützt Claude, GPT und Gemini – wählbar pro Agent (Premium/Budget)
- **Live-Transparenz**: Sieh den Agenten in Echtzeit beim Arbeiten zu
- **Web-Recherche**: Aktuelle Informationen via Tavily Search
- **Session-Logging**: Detaillierte JSON-Logs mit Token-Tracking und Kosten-Schätzung
- **React Frontend**: Modernes UI mit IDLE → PLANNING → PRODUCING → COMPLETE Workflow

## Quick Start

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
cd HayMAS
./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 – Frontend:**
```bash
cd HayMAS/frontend
npm run dev
```

| URL | Beschreibung |
|-----|--------------|
| http://localhost:5173 | **Frontend** (hier arbeiten!) |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | Swagger API-Dokumentation |

## Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    IDLE     │ →  │  PLANNING   │ →  │  PRODUCING  │ →  │  COMPLETE   │
│  Frage      │    │  Plan       │    │  Agenten    │    │  Artikel    │
│  eingeben   │    │  anpassen   │    │  arbeiten   │    │  anzeigen   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 1. IDLE
- Kernfrage eingeben
- Beispielfragen verfügbar
- **Zwei Optionen:**
  - **"Plan erstellen"** → KI analysiert, du kannst anpassen
  - **"Schnellstart"** → Direkt generieren (KI analysiert intern)

### 2. PLANNING (neu!)
- KI analysiert das Thema automatisch
- Schlägt 2-5 Recherche-Runden vor basierend auf:
  - Thementyp (Tech, Business, History, etc.)
  - Zeitrelevanz (aktuell, historisch, zeitlos)
  - Komplexität
- Recherche-Runden können:
  - Aktiviert/deaktiviert werden
  - Suchanfragen bearbeitet werden
- Editor-Review kann ein-/ausgeschaltet werden

**Beispiele für automatische Anpassung:**

| Frage | Runden | Editor | Warum? |
|-------|--------|--------|--------|
| "Warum ist die Banane krumm?" | 2 | Nein | Einfach, zeitlos |
| "Aktuelle KI Tools für Coding?" | 4 | Nein | Tech, aktuell |
| "Rolle der Frau im Nazi-Deutschland" | 5 | Ja | History, komplex, sensibel |

### 3. PRODUCING
- Agenten arbeiten den Plan ab
- Live-Updates in der UI
- Fortschritt wird angezeigt

### 4. COMPLETE
- Artikel wird angezeigt
- Download als Markdown
- **Details-Button** zeigt Session-Log mit Token-Verbrauch und Kosten

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                             │
│     1. Analysiert Thema → erstellt Recherche-Plan           │
│     2. Koordiniert die anderen Agenten                       │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   RESEARCHER    │ │     WRITER      │ │     EDITOR      │
│  Web-Recherche  │ │ Artikel-Text    │ │ Qualitätsprüfung│
│  (2-5 Runden)   │ │                 │ │   (optional)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP SERVER - TOOLS                        │
│              tavily_search  •  save_markdown                 │
└─────────────────────────────────────────────────────────────┘
```

## Verwendete Modelle

Jeder Agent kann zwischen **Premium** und **Budget** Modellen wechseln:

| Agent | Premium | Budget |
|-------|---------|--------|
| Orchestrator | Claude Opus 4.5 | Claude Sonnet 4.5 |
| Researcher | Claude Sonnet 4.5 | GPT-4o |
| Writer | GPT-5.2 | GPT-5.1 |
| Editor | Claude Sonnet 4.5 | Claude Haiku 4.5 |

## Projektstruktur

```
HayMAS/
├── api.py                # FastAPI Backend
├── config.py             # Modell-Konfiguration
├── session_logger.py     # Session-Logging (JSON)
├── requirements.txt      # Python Dependencies
│
├── frontend/             # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Studio.tsx        # Haupt-Container
│   │   │   ├── IdleView.tsx      # Frage-Eingabe
│   │   │   ├── PlanningView.tsx  # Plan-Editor (NEU)
│   │   │   ├── ProducingView.tsx # Live-Fortschritt
│   │   │   ├── CompleteView.tsx  # Artikel-Anzeige
│   │   │   ├── LogDrawer.tsx     # Session-Log Anzeige
│   │   │   └── SettingsDrawer.tsx# Modell-Einstellungen
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   └── package.json
│
├── agents/               # KI-Agenten
│   ├── base_agent.py     # Basis mit ReAct-Loop & Token-Tracking
│   ├── orchestrator.py   # Themenanalyse & Workflow-Koordination
│   ├── researcher.py     # Web-Recherche
│   ├── writer.py         # Artikel-Erstellung
│   └── editor.py         # Qualitätsprüfung
│
├── mcp_server/           # Tool-Server
│   └── tools/
│       ├── tavily_search.py
│       └── file_tools.py
│
├── output/               # Generierte Artikel (*.md)
└── logs/                 # Session-Logs (*.json)
```

## API Endpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/` | GET | API-Info + Links |
| `/api/status` | GET | API-Key Status |
| `/api/models` | GET | Verfügbare Modelle |
| `/api/articles` | GET | Liste aller Artikel |
| `/api/articles/{filename}` | GET | Artikel-Inhalt |
| `/api/articles/{filename}/log` | GET | Session-Log für Artikel |
| `/api/analyze` | POST | Themenanalyse → Recherche-Plan |
| `/api/generate` | POST | Artikel generieren (SSE) |
| `/api/logs` | GET | Liste aller Session-Logs |
| `/api/logs/{filename}` | GET | Einzelnes Session-Log |

## Session-Logging

Jede Artikel-Generierung erstellt ein detailliertes JSON-Log:

```json
{
  "session_id": "20260117_230432",
  "question": "...",
  "settings": {
    "research_rounds": 5,
    "use_editor": true,
    "tiers": { "orchestrator": "premium", ... },
    "plan": { ... }
  },
  "timeline": [
    {
      "agent": "Researcher",
      "model": "claude-sonnet-4-5",
      "action": "research_round_1",
      "duration_ms": 26957,
      "tokens": { "input": 3603, "output": 1242 },
      "tool_calls": ["tavily_search"],
      "status": "success"
    },
    ...
  ],
  "summary": {
    "total_duration_ms": 424037,
    "total_tokens": { "input": 50043, "output": 19772 },
    "estimated_cost_usd": 0.45,
    "article_words": 2431
  }
}
```

## Troubleshooting

### "Analyse fehlgeschlagen" beim Klick auf "Plan erstellen"
- Prüfe ob das Backend läuft: `curl http://localhost:8000/`
- Backend neu starten: `./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload`

### 404 Fehler bei API-Calls
- Frontend und Backend müssen beide laufen (zwei Terminals!)
- Prüfe ob Port 8000 frei ist: `lsof -i:8000`

### Rate Limit Fehler (429)
- Anthropic hat Limits von ~30.000 Tokens/Minute
- Wechsle betroffene Agenten auf "Budget" Modelle in den Settings

### Artikel wird nicht geladen nach Generierung
- Kurz warten, dann Seite neu laden
- Artikel ist im `output/` Ordner gespeichert

## Entwicklung

Für Entwicklung mit Auto-Reload:

```bash
# Backend mit --reload Flag
./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Frontend (hat bereits HMR)
npm run dev
```

Dokumentation der Chat-Verläufe: siehe `CursorChat.md`

## Lizenz

MIT
