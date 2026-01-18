# Multi-Agenten-System (MAS) Konzept: Präsentations-Generator

## Anwendungsfall

Automatische Erstellung von Präsentationen (10-15 Folien) zu komplexen Fachthemen.

**Beispiel-Kernfrage:**
> "Wie funktioniert konzeptionell und technisch ein Chatbot, der Insassen im Justizvollzug bei Fragen zum Antragswesen unterstützt? Der Chatbot muss auf große Informationsmengen (Excel, PDFs) zugreifen können, ohne diese komplett als Kontext zu laden."

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                            │
│                                                             │
│  Aufgaben:                                                  │
│  • Plant die Gliederung (10-15 Folien)                     │
│  • Delegiert an spezialisierte Agenten                     │
│  • Qualitätssicherung der Zwischenergebnisse               │
│  • Koordiniert den Gesamtprozess                           │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│ RECHERCHE-AGENT │            │ STRUKTUR-AGENT  │
│                 │            │                 │
│ • Web-Suche     │            │ • Erstellt MD   │
│   (Tavily)      │            │   mit Folien-   │
│ • LLM-Wissen    │            │   Struktur      │
│   nutzen        │            │ • Definiert     │
│ • Quellen       │            │   Inhalte pro   │
│   kombinieren   │            │   Folie         │
└─────────────────┘            └─────────────────┘
                                       │
                                       ▼
                               ┌─────────────────┐
                               │   PPT-TOOL      │
                               │   (kein Agent!) │
                               │                 │
                               │ • Template +    │
                               │   MD-Struktur   │
                               │ • = fertige PPT │
                               └─────────────────┘
```

---

## Agenten-Rollen

### 1. Orchestrator
- **LLM:** Claude 3.5 Sonnet (empfohlen) oder GPT-4o
- **Rolle:** Projektmanager / Koordinator
- **Aufgaben:**
  - Aufgabe analysieren und Gliederung planen
  - Agenten in richtiger Reihenfolge aufrufen
  - Zwischenergebnisse prüfen (Qualitätssicherung)
  - Bei Bedarf Nachbesserung anfordern

### 2. Recherche-Agent
- **LLM:** Claude oder GPT-4o
- **Tools:** Tavily (Web-Suche)
- **Aufgaben:**
  - Aktuelle Informationen im Web recherchieren
  - LLM-Wissen mit Recherche-Ergebnissen kombinieren
  - Strukturierte Zusammenfassung der Erkenntnisse

### 3. Struktur-Agent
- **LLM:** Claude oder GPT-4o
- **Aufgaben:**
  - Recherche-Ergebnisse in Präsentationsstruktur überführen
  - Markdown-Datei mit klarer Folien-Aufteilung erstellen
  - Sprechertexte und Stichpunkte pro Folie

### 4. PPT-Tool (kein Agent!)
- **Technologie:** python-pptx, Marp, oder Google Slides API
- **Aufgaben:**
  - MD-Struktur in PowerPoint überführen
  - Vordefiniertes Design-Template anwenden

---

## Warum kein Design-Agent?

**LLMs können kein visuelles Design!**

Sie können nicht:
- Farben harmonisch auswählen
- Layouts visuell gestalten
- PowerPoint-Folien "schön machen"

**Lösung:** Template-basierter Ansatz
- Professionelle Vorlagen vorab erstellen
- Agent liefert nur strukturierte Inhalte
- Tool wendet Template automatisch an

---

## Workflow

```
1. User gibt Thema/Kernfrage ein

2. Orchestrator analysiert:
   → "Das ist eine Frage zu RAG-Chatbots"
   → "Ich brauche: Konzept + Technik + Use Case"
   → Plant 12 Folien

3. Orchestrator → Recherche-Agent:
   → "Recherchiere RAG-Architekturen für Chatbots"
   → "Finde Best Practices für Dokumenten-Chatbots"

4. Recherche-Agent liefert Ergebnisse

5. Orchestrator prüft (QS):
   → "Ist das vollständig? Fehlt etwas?"
   → Bei Bedarf: Nachrecherche anfordern

6. Orchestrator → Struktur-Agent:
   → "Erstelle Folien-Struktur aus diesen Inhalten"
   → Übergibt Recherche-Ergebnisse

7. Struktur-Agent liefert MD-Datei:
   # Folie 1: Titel
   # Folie 2: Problemstellung
   # Folie 3: Lösungsansatz RAG
   ...

8. Orchestrator prüft (QS):
   → "Sind alle wichtigen Punkte drin?"
   → "Ist der rote Faden erkennbar?"

9. Orchestrator → PPT-Tool:
   → MD-Datei + Template = fertige Präsentation

10. Fertige PPT wird ausgegeben
```

---

## Technische Umsetzung

### Benötigte API-Keys
- **LLM:** Anthropic (Claude) oder OpenAI (GPT-4)
- **Web-Suche:** Tavily

### Mögliche Tech-Stacks

**Option A: Python-basiert**
- LangChain oder eigene Implementierung
- python-pptx für PPT-Generierung
- Tavily Python SDK

**Option B: In bestehendes Tool integrieren**
- Als Erweiterung für TypeGodMD
- Agenten als spezialisierte Chat-Modi

### PPT-Generierung
- **Marp:** Markdown → Präsentation (einfach)
- **python-pptx:** Volle Kontrolle über PPT
- **Google Slides API:** Cloud-basiert

---

## Beispiel: Ausgabe des Struktur-Agenten

```markdown
# Folie 1: Titel
**RAG-Chatbot für das Antragswesen im Justizvollzug**
Konzept und technische Umsetzung

# Folie 2: Problemstellung
- Insassen haben Fragen zu Anträgen
- Informationen verteilt auf Excel, PDFs
- Zu viel Kontext für direkten LLM-Aufruf

# Folie 3: Lösungsansatz - RAG
- Retrieval Augmented Generation
- Dokumente werden vektorisiert
- Nur relevante Teile werden geladen

# Folie 4: Architektur-Übersicht
[Diagramm: Dokumente → Embedding-DB → LLM → Antwort]

# Folie 5: Technischer Stack
- Embedding-Modell: text-embedding-3-small
- Vektor-DB: Pinecone / ChromaDB
- LLM: Claude 3.5 Sonnet
...
```

---

## Abgrenzung: Agent vs. Tool

| Komponente | Agent? | Begründung |
|------------|--------|------------|
| Orchestrator | ✅ Ja | Entscheidet, plant, koordiniert |
| Recherche | ✅ Ja | Kombiniert Suche + Analyse |
| Struktur | ✅ Ja | Kreative Aufbereitung |
| PPT-Generierung | ❌ Nein | Mechanische Umwandlung |
| Design | ❌ Nein | LLMs können kein visuelles Design |

---

## Erweiterungsmöglichkeiten

1. **Gemini-Integration:** Für sehr große Quelldokumente (1M Token Kontext)
2. **Feedback-Loop:** User kann Zwischenergebnisse kommentieren
3. **Template-Auswahl:** Verschiedene Designs je nach Zielgruppe
4. **Export-Formate:** PPT, Google Slides, PDF, Web (reveal.js)

---

## Offene Fragen / Nächste Schritte

- [ ] Tech-Stack entscheiden (Python standalone vs. TypeGodMD-Integration)
- [ ] PPT-Templates erstellen
- [ ] Prototyp mit einem Thema testen
- [ ] Prompt-Engineering für jeden Agenten
