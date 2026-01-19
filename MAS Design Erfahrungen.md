# MAS Design Erfahrungen

Dokumentation unserer Lernreise bei der Entwicklung eines Multi-Agenten-Systems für hochwertige Wissensartikel.

---

## Design 1: "Search-First" (Recherche zuerst)

### Ansatz
```
Themenanalyse → Recherche-Plan → X Runden Suche → Writer fasst zusammen → Editor prüft
```

### Wie es funktionierte
1. Orchestrator analysiert Frage, erstellt Recherche-Plan
2. Researcher führt 5-8 Suchrunden mit verschiedenen Tools durch
3. Jede Runde: Keyword-basierte Suche (Tavily, Wikipedia, etc.)
4. Writer bekommt alle Recherche-Ergebnisse, schreibt Artikel
5. Editor prüft optional

### Ergebnis
- ✅ **Viele Quellen** (15-25 externe Referenzen)
- ✅ **Diverse Tools** (Wikipedia, Tavily, GNews, HackerNews, etc.)

### Das Problem
- ❌ **LLM "vergisst" eigenes Wissen**
- ❌ **Sucht nach falschen Begriffen** 

**Konkretes Beispiel:**  
Frage: *"Was ist ServiceNow mit Agent Builder?"*

- User meinte: **Build Agent** / **AI Agent Studio**
- LLM suchte wörtlich nach: "Agent Builder"
- Tavily fand: Nichts Relevantes
- Ergebnis im Artikel: *"Zu 'Agent Builder' wurden keine Informationen gefunden"*

**Absurdität:** Das LLM WUSSTE was Build Agent ist (aus Training), aber weil es gezwungen war zu suchen, und die Suche nichts fand, schrieb es "nicht gefunden" - obwohl eine direkte ChatGPT-Frage sofort die richtige Antwort geliefert hätte.

### Kernproblem
> Das System macht das LLM "dumm", indem es ihm verbietet, sein eigenes Wissen zu nutzen.

---

## Design 2: "Knowledge-First" (LLM-Wissen zuerst)

### Ansatz
```
DraftWriter (GPT) schreibt mit eigenem Wissen 
→ Markiert unsichere Stellen [FACT-CHECK], [RECHERCHE]
→ Gezielte Recherche nur für Markierungen
→ Integration → Editor prüft
```

### Wie es funktionierte
1. DraftWriter (GPT-5.2) erstellt Expertenentwurf aus Training
2. Soll Markierungen setzen: `[FACT-CHECK]`, `[RECHERCHE]`, `[QUELLE]`, `[UNSICHER]`
3. Researcher recherchiert NUR für markierte Stellen
4. Writer integriert Recherche in Entwurf
5. Editor (Claude) prüft

### Ergebnis
- ✅ **Fundierter Artikel** (18.000+ Zeichen, Expertenwissen)
- ✅ **Build Agent korrekt erklärt** (LLM wusste es!)

### Das Problem
- ❌ **0 Markierungen gesetzt** - GPT war zu selbstsicher
- ❌ **0 Recherchen durchgeführt** - weil keine Markierungen
- ❌ **Nur 4 Quellen** - alle von ServiceNow selbst
- ❌ **Gemini nie verwendet** - obwohl "integriert"
- ❌ **Claude sagte "REVISE"** - wurde ignoriert

**Konkretes Ergebnis:**  
- GPT-5.2: 100% der Arbeit
- Claude: Sagte "könnte besser sein", wurde ignoriert
- Gemini: Gar nicht aufgerufen

### Kernproblem
> Ein Marketing-Artikel mit Extra-Schritten. Wissenschaftlich unbrauchbar (keine unabhängigen Quellen).

**Prof-Test:** *"Das ist ein gut geschriebener Hersteller-Text, keine wissenschaftliche Arbeit."*

---

## Design 3: "Triangulation" (Multi-LLM Kollaboration) - VORSCHLAG

### Kern-Insight
Jedes LLM hat unterschiedliche Stärken:

| LLM | Stärke |
|-----|--------|
| **Claude** | Kritisches Denken, gibt Unsicherheiten zu |
| **GPT-5.2** | Breites Wissen, flüssiger Schreibstil |
| **Gemini** | Google Search, Aktualität |

### Ansatz
```
Claude identifiziert Lücken → Tools + Gemini recherchieren → GPT schreibt → Claude prüft
```

### Der Flow

#### Phase 1: CLAUDE als kritischer Analyst
Claude bekommt die **Frage** (noch keinen Artikel) und analysiert ehrlich:

```
🧠 Was weiß ich SICHER?
   → ServiceNow ist Enterprise-Plattform, Now Assist existiert...

❓ Was ist mir UNSICHER?  
   → Ist "Build Agent" offizielles Produkt oder Marketing?
   → Wann released? Welche Version?

📅 Was braucht AKTUELLE Daten?
   → Pricing, neueste Features 2025

📚 Was braucht externe QUELLEN?
   → Technische Architektur, Vergleich zu Wettbewerbern
```

**Output:** Konkrete Recherche-Aufträge mit Tool-Zuordnung

#### Phase 2: Gezielte Recherche mit PASSENDEN TOOLS
Nicht "Gemini für alles", sondern intelligente Tool-Auswahl:

| Lücken-Typ | Tool |
|------------|------|
| Wissenschaftliche Frage | Semantic Scholar, arXiv |
| Aktuelle News | GNews |
| Tech-Meinungen | HackerNews |
| Grundlagen | Wikipedia |
| Allgemeine Fakten | Tavily |
| EU/Behörden | TED |
| Aktualitäts-Check | Gemini Search |

#### Phase 3: GPT schreibt den Artikel
GPT bekommt:
- Claudes strukturierte Analyse
- Alle Recherche-Ergebnisse mit Quellen
- Auftrag: Kombiniere eigenes Wissen + externe Fakten

#### Phase 4: Doppelte Prüfung
- **Claude:** Logik, Struktur, alle Lücken geschlossen?
- **Gemini:** Aktualität, gibt es neuere Infos?

### Warum das funktionieren sollte

| Problem Design 1 | Problem Design 2 | Lösung Design 3 |
|------------------|------------------|-----------------|
| LLM vergisst Wissen | Keine externen Quellen | Claude identifiziert was fehlt |
| Falsche Suchbegriffe | GPT zu selbstsicher | Claude ist ehrlich über Grenzen |
| Zu viel irrelevante Suche | Zu wenig Recherche | Gezielte Recherche für echte Lücken |
| Ein LLM macht alles | Ein LLM macht alles | 3 LLMs mit spezialisierten Rollen |

### Erwartetes Ergebnis
- ✅ Fundiertes Expertenwissen (aus GPT)
- ✅ Ehrliche Lücken-Identifikation (durch Claude)
- ✅ Diverse externe Quellen (durch spezialisierte Tools)
- ✅ Aktualität (durch Gemini)
- ✅ Qualitätssicherung (durch Claude + Gemini)

---

## Zusammenfassung

| Aspekt | Design 1 | Design 2 | Design 3 |
|--------|----------|----------|----------|
| **Quellen** | Viele (15-25) | Wenige (4) | Gezielt (10-20) |
| **LLM-Wissen** | Ignoriert | Überdominant | Balanciert |
| **Recherche** | Zu breit | Keine | Gezielt |
| **Multi-LLM** | Nein | Pseudo | Echte Kollaboration |
| **Wissenschaftlich** | Mittelmäßig | Mangelhaft | Angestrebt |

---

## Offene Fragen für Design 3

1. Wie zwingen wir Claude, wirklich ehrlich über Unsicherheiten zu sein?
2. Wie verhindern wir, dass die Tool-Auswahl zu komplex wird?
3. Wie messen wir "Artikelqualität" objektiv?
4. Was ist die optimale Anzahl an Recherchen (Balance: Qualität vs. Kosten)?

---

*Dokumentiert am 19. Januar 2026*
