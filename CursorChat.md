# HayMAS - Entwicklungs-Dokumentation

Zusammenfassung der Chat-Verläufe mit Cursor AI zur Entwicklung von HayMAS.

---

## 📅 Projekthistorie

### Phase 1: Grundgerüst (Frühe Entwicklung)

**Ziel:** Multi-Agenten-System für Wissensartikel-Generierung

**Erstellte Komponenten:**
- `config.py` - API-Keys und Modell-Konfiguration
- `agents/base_agent.py` - Basis-Agent mit ReAct-Loop
- `agents/orchestrator.py` - Workflow-Koordination
- `agents/researcher.py` - Web-Recherche
- `agents/writer.py` - Artikel-Erstellung
- `agents/editor.py` - Qualitätsprüfung
- `mcp_server/` - Tool-Server (tavily_search, file_tools)

**LLM-Integration:**
- Anthropic Claude (Opus, Sonnet, Haiku)
- OpenAI GPT (5.2, 5.1, 4o)
- Google Gemini (Deep Research, 3 Pro, 2.5 Flash)

---

### Phase 2: Streamlit UI (Deprecated)

**Datei:** `app.py`

Erste UI-Version mit Streamlit. Probleme:
- `StreamlitAPIException` bei Session-State Updates
- Komplexe State-Verwaltung
- UI sah trotz Iterationen "wie ein Prototyp" aus
- Später ersetzt durch React-Frontend

**Konzeptionelle Analyse (vor Migration):**
- Streamlit ist gut für Data-Apps, nicht für "Studio"-Feeling
- Problem: Kein klares mentales Modell (Dashboard? Editor? Workflow?)
- Lösung: Klare Produkt-Metapher "AI Writing Studio" definieren

---

### Phase 3: React Frontend + FastAPI Backend

**Migration von Streamlit zu:**
- `api.py` - FastAPI Backend mit SSE (Server-Sent Events)
- `frontend/` - React + TypeScript + Tailwind CSS

**Workflow:** IDLE → PRODUCING → COMPLETE

---

### Phase 4: Bugfixing Anthropic Tool Calls

**Problem:** `tool_use ids without tool_result blocks` Error

**Ursache:** Claude macht **parallele Tool-Calls**, aber der Code verarbeitete nur den ersten.

**Lösung:**
1. `_call_claude` sammelt alle `tool_use` Blocks
2. `run()` Loop iteriert durch alle Tool-Calls
3. Tool-Results werden korrekt formatiert

**Relevanter Code in `base_agent.py`:**
```python
# Tool-Result für Anthropic formatieren
self.messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": msg["tool_use_id"],
        "content": json.dumps(msg["result"], ensure_ascii=False)
    }]
})
```

---

### Phase 5: Token-Explosion & Rate Limits

**Problem:** Anthropic API `rate_limit_error` (429) - 30.000 Input Tokens/Minute überschritten

**Ursache:** Gesamter Konversationsverlauf mit Tool-Results wurde bei jedem API-Call gesendet.

**Lösung (Option C - Kombiniert):**

1. **Tool-Result Truncation:**
   ```python
   MAX_TOOL_RESULT_CHARS = 1500  # in config.py
   
   def _truncate_result(self, result: Dict) -> Dict:
       # Kürzt zu lange Ergebnisse automatisch
   ```

2. **Single-Shot Researcher:**
   - Researcher führt nur EINE Suche pro Aufruf durch
   - Orchestrator ruft Researcher mehrfach auf
   - `researcher.reset()` zwischen den Runden

---

### Phase 6: Infinite Loop Fix

**Problem:** Editor-Writer Feedback-Schleife lief endlos.

**Lösung:**
```python
MAX_EDITOR_ITERATIONS = 2  # in config.py
```

Orchestrator bricht nach 2 Iterationen ab.

---

### Phase 7: Session-Logging (17.01.2026)

**Neue Datei:** `session_logger.py`

**Features:**
- JSON-Logs pro Session
- Persistenz nach jedem Schritt (auch bei Abbruch)
- Token-Tracking pro Agent
- Kosten-Schätzung
- Timeline aller Schritte

**Log-Struktur:**
```json
{
  "session_id": "20260117_215119",
  "timeline": [
    {
      "agent": "Researcher",
      "model": "gpt-4o",
      "duration_ms": 7707,
      "tokens": { "input": 1375, "output": 274 },
      "tool_calls": ["tavily_search"],
      "status": "success"
    }
  ],
  "summary": {
    "total_tokens": { "input": 40271, "output": 17632 },
    "estimated_cost_usd": 0.39
  }
}
```

**Neue API-Endpoints:**
- `GET /api/logs`
- `GET /api/logs/{filename}`
- `GET /api/articles/{filename}/log`

**Frontend:**
- `LogDrawer.tsx` - Details-Button zeigt Session-Log

---

### Phase 8: Intelligente Themenanalyse (17.01.2026)

**Neuer Workflow:** IDLE → **PLANNING** → PRODUCING → COMPLETE

**Features:**
1. **Automatische Themenanalyse:**
   - Orchestrator analysiert Kernfrage
   - Bestimmt: topic_type, time_relevance, complexity
   - Schlägt 2-5 Recherche-Runden vor

2. **Plan-Editor (PlanningView.tsx):**
   - Runden aktivieren/deaktivieren
   - Suchanfragen bearbeiten
   - Editor ein-/ausschalten

**Neue Datenstrukturen:**
```python
@dataclass
class ResearchRound:
    name: str
    focus: str
    search_query: str
    enabled: bool = True

@dataclass
class ResearchPlan:
    topic_type: str
    time_relevance: str
    complexity: str
    rounds: List[ResearchRound]
    use_editor: bool
    reasoning: str
```

**Neuer API-Endpoint:**
- `POST /api/analyze` - Themenanalyse

**Bug-Fix: JSON-Parsing (18.01.2026)**

Das LLM gibt manchmal `recommended_rounds` statt `rounds` zurück. Fix in `from_dict`:
```python
# Unterstütze sowohl "rounds" als auch "recommended_rounds" (LLM-Variation)
raw_rounds = data.get("rounds") or data.get("recommended_rounds", [])
```

**UI-Entscheidungen:**
- **"Plan erstellen"** → KI analysiert, User kann anpassen
- **"Schnellstart"** → Direkt generieren (KI analysiert intern)
- Alte Slider für Recherche-Runden in Settings entfernt (jetzt dynamisch pro Thema)

---

### Phase 3 Details: React Migration

**Hintergrund:** Streamlit lieferte trotz mehrerer Iterationen kein professionelles UI. React/Tailwind war die bessere Wahl.

**Konzeptionelle Metapher:** "AI Writing Studio" (nicht Dashboard, nicht Editor)

**State-Machine:**
```
IDLE → ANALYZING → PLANNING → PRODUCING → COMPLETE
         ↓            ↓           ↓
      (optional)   (optional)  (streaming)
```

**Server-Setup (zwei Terminals!):**
```bash
# Terminal 1: Backend
cd HayMAS && ./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd HayMAS/frontend && npm run dev
```

**Frontend:** http://localhost:5173  
**Backend API:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs

**Vite Proxy-Config (`vite.config.ts`):**
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

---

## 🔧 Optimierungspotenziale (Detailliert)

**Basierend auf Log-Analyse der Session 20260117_215119:**

```
Gesamtdauer:    4:19 Min (258.839ms)
Total Tokens:   57.903 (40k in / 18k out)
Kosten:         $0.39
Artikel:        3.482 Wörter
```

---

### 🔴 PRIO 1: Writer Output-Länge begrenzen

**Problem:**
```
Writer:     120s (46% der Gesamtzeit)
Revision:    89s (34% der Gesamtzeit)
─────────────────────────────────────
Summe:      209s von 259s total = 80%!
```

Der Writer produziert sehr lange Texte (25k → 29k Zeichen nach Revision).

**Erwarteter Effekt:** -50% Zeit, -30% Kosten

**Umsetzung in `agents/writer.py`:**
```python
WRITER_SYSTEM_PROMPT = """...
## WICHTIGE EINSCHRÄNKUNGEN:
- Maximale Artikellänge: 2500 Wörter
- Fokussiere auf Kernaussagen, vermeide Redundanz
- Jeder Abschnitt sollte max. 300-400 Wörter haben
..."""
```

**Oder in `orchestrator.py` beim Writer-Task:**
```python
writer_task = f"""Erstelle einen Wissensartikel zur Kernfrage: {core_question}

WICHTIG: 
- Maximale Länge: 2500 Wörter
- Nutze NUR Informationen aus der Recherche
- Keine Wiederholungen oder Fülltext
"""
```

**Status:** ⏳ Nicht umgesetzt

---

### 🔴 PRIO 2: Budget-Modelle überdenken

**Problem:**
GPT-5.1 ist als "Budget" konfiguriert, ist aber fast so teuer wie GPT-5.2.

**Aktuelle Konfiguration (`config.py`):**
```python
AGENT_MODELS = {
    "writer": AgentModelConfig(
        premium="gpt-5.2",
        budget="gpt-5.1",  # ← Immer noch teuer!
    ),
}
```

**Preisvergleich (geschätzt):**
| Modell | Input/1M | Output/1M | Kategorie |
|--------|----------|-----------|-----------|
| GPT-5.2 | ~$10 | ~$30 | Premium |
| GPT-5.1 | ~$8 | ~$24 | Premium |
| GPT-4o | ~$2.50 | ~$10 | **Echtes Budget** |
| GPT-4o-mini | ~$0.15 | ~$0.60 | **Sehr günstig** |

**Empfohlene Änderung:**
```python
AGENT_MODELS = {
    "orchestrator": AgentModelConfig(
        premium="claude-opus-4-5",
        budget="gpt-4o-mini",  # War: claude-sonnet-4-5
    ),
    "researcher": AgentModelConfig(
        premium="claude-sonnet-4-5",
        budget="gpt-4o-mini",  # War: gpt-4o
    ),
    "writer": AgentModelConfig(
        premium="gpt-5.2",
        budget="gpt-4o",  # War: gpt-5.1
    ),
    "editor": AgentModelConfig(
        premium="claude-sonnet-4-5",
        budget="claude-haiku-4-5",  # OK, Haiku ist günstig
    ),
}
```

**Erwarteter Effekt:** -40% Kosten bei Budget-Runs

**Status:** ⏳ Nicht umgesetzt

---

### 🟡 PRIO 3: Recherche parallelisieren

**Problem:**
```
Research Round 1: 7.7s
Research Round 2: 7.0s
Research Round 3: 8.6s
───────────────────────
Sequenziell:     23.3s
Parallel:        ~8s (längste Runde)
Ersparnis:       ~15s
```

**Umsetzung:**

Option A: `asyncio` in Python
```python
import asyncio

async def research_parallel(self, rounds: List[ResearchRound]):
    tasks = [
        self._research_single(round) 
        for round in rounds
    ]
    results = await asyncio.gather(*tasks)
    return results
```

Option B: `concurrent.futures`
```python
from concurrent.futures import ThreadPoolExecutor

def research_parallel(self, rounds):
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(self._research_single, rounds))
    return results
```

**Herausforderung:** 
- SSE-Events müssen trotzdem in richtiger Reihenfolge gesendet werden
- Oder: Events mit Round-ID taggen, Frontend sortiert

**Erwarteter Effekt:** -15s Dauer (bei 3 Runden)

**Status:** ⏳ Nicht umgesetzt

---

### 🟡 PRIO 4: Editor-Prompt anpassen

**Problem:**
```
Artikel VOR Editor:   24.911 Zeichen
Artikel NACH Editor:  29.424 Zeichen (+18%!)
```

Der Editor fordert "mehr Details" statt zu straffen.

**Aktueller Prompt (`orchestrator.py`):**
```python
editor_task = """Prüfe den folgenden Wissensartikel auf Qualität:
1. Ist der Artikel relevant zur Kernfrage?
2. Ist er gut strukturiert?
3. Sind die Informationen korrekt und vollständig?
4. Gibt es Verbesserungsvorschläge?
"""
```

**Verbesserter Prompt:**
```python
editor_task = """Prüfe den Wissensartikel kritisch:

## PRÜFKRITERIEN:
1. Relevanz: Beantwortet der Artikel die Kernfrage?
2. Struktur: Ist die Gliederung logisch?
3. Fakten: Stimmen die Informationen mit der Recherche überein?
4. Redundanz: Gibt es Wiederholungen oder Fülltext?

## FEEDBACK-REGELN:
- Empfehle KÜRZUNGEN bei redundanten Passagen
- Empfehle KEINE Erweiterungen außer bei faktischen Lücken
- Ziel: Prägnant und fokussiert, nicht länger
- Wenn der Artikel gut ist: Schreibe "KEINE WEITEREN ÄNDERUNGEN"
"""
```

**Erwarteter Effekt:** -20% Tokens, kürzere Artikel

**Status:** ⏳ Nicht umgesetzt

---

### 🟢 PRIO 5: Fakten-Coverage tracken

**Problem:**
```
Research Input:   ~4.200 Zeichen (3 Runden)
Artikel Output:  ~25.000 Zeichen
Verhältnis:      1:6
```

Der Writer "erfindet" viel Content, der nicht aus der Recherche stammt.

**Idee:** Nach der Generierung prüfen, welche Research-Fakten verwendet wurden.

**Mögliche Umsetzung:**
1. **Einfach:** Research-Ergebnisse als "Quellen" nummerieren [1], [2], ...
2. **Mittel:** Writer muss Quellen zitieren, Editor prüft Coverage
3. **Aufwändig:** Embedding-Vergleich Research ↔ Artikel-Absätze

**Beispiel für Writer-Prompt:**
```python
writer_task = """Erstelle einen Wissensartikel.

QUELLENVERWENDUNG:
- Nummeriere jede Recherche-Runde als [Quelle 1], [Quelle 2], etc.
- Zitiere Fakten mit [1], [2], etc. im Text
- Am Ende: Quellenverzeichnis mit allen verwendeten Quellen
"""
```

**Erwarteter Effekt:** +Qualität, +Transparenz

**Status:** ⏳ Nicht umgesetzt

---

### 🟢 PRIO 6: Research-Limit erhöhen

**Problem:**
Tool-Results werden auf 1.500 Zeichen gekürzt (MAX_TOOL_RESULT_CHARS).

**Aktuell (`config.py`):**
```python
MAX_TOOL_RESULT_CHARS = 1500  # ~400 Tokens
```

**Trade-off:**
- Höheres Limit = Mehr Kontext für Writer = Bessere Fakten
- Höheres Limit = Mehr Tokens = Höhere Kosten

**Empfehlung:**
```python
MAX_TOOL_RESULT_CHARS = 2500  # ~600 Tokens, +66%
```

Bei 3 Runden: +3 × 1000 = 3.000 Zeichen mehr ≈ +750 Tokens ≈ +$0.02

**Status:** ⏳ Nicht umgesetzt

---

## 📊 Zusammenfassung Optimierungen

| # | Optimierung | Effekt | Aufwand | Status |
|---|-------------|--------|---------|--------|
| 🔴1 | Writer Output begrenzen | -50% Zeit, -30% Kosten | Gering | ⏳ |
| 🔴2 | Budget-Modelle (GPT-4o) | -40% Kosten | Gering | ⏳ |
| 🟡3 | Recherche parallelisieren | -15s Dauer | Mittel | ⏳ |
| 🟡4 | Editor-Prompt anpassen | -20% Tokens | Gering | ⏳ |
| 🟢5 | Fakten-Coverage tracken | +Qualität | Hoch | ⏳ |
| 🟢6 | Research-Limit erhöhen | +Qualität | Gering | ⏳ |

**Quick Wins (< 30 Min Aufwand):**
- Budget-Modelle ändern (config.py)
- Writer-Prompt anpassen (orchestrator.py)
- Editor-Prompt anpassen (orchestrator.py)
- Research-Limit erhöhen (config.py)

---

## 📁 Wichtige Dateien

### Backend
- `api.py` - FastAPI Server mit allen Endpoints
- `config.py` - Alle Konfigurationen (API-Keys, Modelle, Limits)
- `session_logger.py` - JSON-Logging mit Kosten-Tracking
- `agents/orchestrator.py` - Hauptlogik + `analyze_topic()` + `ResearchPlan`
- `agents/base_agent.py` - ReAct-Loop für alle Agents
- `agents/researcher.py` - Tavily Web-Suche
- `agents/writer.py` - Artikel-Generierung
- `agents/editor.py` - Qualitätsprüfung

**Alle API-Endpoints:**
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | API-Info + Links |
| `/api/status` | GET | API-Key Status |
| `/api/models` | GET | Verfügbare Modelle |
| `/api/articles` | GET | Liste aller Artikel |
| `/api/articles/{filename}` | GET | Artikel-Inhalt |
| `/api/articles/{filename}/log` | GET | Session-Log zum Artikel |
| `/api/logs` | GET | Alle Logs |
| `/api/logs/{filename}` | GET | Einzelnes Log |
| `/api/analyze` | POST | Themenanalyse → Plan |
| `/api/generate` | POST | Artikel generieren (SSE) |

### Frontend
- `frontend/src/components/Studio.tsx` - Haupt-Container, routet zwischen Views
- `frontend/src/components/IdleView.tsx` - Eingabe + "Plan erstellen" / "Schnellstart"
- `frontend/src/components/PlanningView.tsx` - Plan-Editor mit Toggle/Edit
- `frontend/src/components/ProducingView.tsx` - Live Event-Stream während Generierung
- `frontend/src/components/CompleteView.tsx` - Fertiger Artikel mit Download
- `frontend/src/components/Header.tsx` - Top-Navigation mit API-Status
- `frontend/src/components/ArchiveDrawer.tsx` - Liste aller Artikel
- `frontend/src/components/SettingsDrawer.tsx` - Modell-Tiers (Premium/Budget)
- `frontend/src/components/LogDrawer.tsx` - Session-Log Details
- `frontend/src/hooks/useStudio.ts` - Zentrale State-Machine
- `frontend/src/lib/api.ts` - API-Client (fetch + SSE)
- `frontend/src/types/index.ts` - TypeScript Interfaces

### Output
- `output/` - Generierte Markdown-Artikel
- `logs/` - Session-Logs (JSON)

---

## 🎯 Dynamische Themenanalyse - Beispiele

Die KI passt die Recherche-Strategie automatisch an:

| Frage | topic_type | Runden | Editor |
|-------|------------|--------|--------|
| "Warum ist die Banane krumm?" | science | 2 | Nein |
| "Was sind aktuelle KI Tools für AI Coding?" | tech | 4 | Nein |
| "Rolle der Frau im Nazi-Deutschland" | history | 4-5 | Ja |
| "Wie funktioniert RAG?" | tech | 3 | Nein |

**Analysierte Dimensionen:**
- `topic_type`: tech, science, history, business, culture, general
- `time_relevance`: current, recent, historical, timeless
- `complexity`: simple, medium, complex
- `needs_current_data`: true/false
- `geographic_focus`: global, regional, local, none

---

## 🚀 Nächste Schritte (Ideen)

1. **Parallelisierung der Recherche** - ~15s Zeitersparnis
2. **Fakten-Coverage Tracking** - Prüfen ob Research genutzt wird
3. **Quellen-Annotation** - [1], [2], ... im Artikel
4. **Budget-Modelle anpassen** - GPT-4o statt GPT-5.1
5. **Writer Output begrenzen** - Max. 2500 Wörter
6. **Drag & Drop für Recherche-Runden** - Reihenfolge ändern

---

## 📞 Kontakt

Entwickelt mit Cursor AI.
Stand: 18. Januar 2026
