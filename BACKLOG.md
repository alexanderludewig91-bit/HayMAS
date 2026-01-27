# HayMAS Backlog

Geplante Features und Verbesserungen für das Multi-Agenten-System.

---

## 🔴 PRIORITÄT: Evidence-Gated Flow Fixes

Diese Issues müssen als nächstes behoben werden!

| Status | Issue | Beschreibung | Auswirkung |
|--------|-------|--------------|------------|
| ✅ | **ClaimMiner JSON-Parsing** | `_parse_json_robust` mit mehreren Fallback-Strategien | Behoben! |
| ✅ | **Halluzinations-Check via Editor** | Editor-Prompt mit ClaimRegister + Quellen, expliziter `type="hallucination"` | Implementiert! |
| ⏸️ | **Gemini-Verifikation (optional)** | Cross-LLM als Premium-Feature für kritische Artikel | Auf Eis - Editor funktioniert |
| ⬜ | **Independence Score** | C-Claims brauchen 2+ **unabhängige** Quellen (nicht vom selben Publisher) | Quellenvielfalt nicht garantiert |
| ❌ | ~~Claim Coverage Tracking~~ | ~~Prüfen ob alle Claims im Artikel~~ | **Verworfen** - Editor darf Claims entfernen! |
| ⬜ | **Modell-Fallbacks** | Graceful Fallback wenn Modell nicht verfügbar | API-Fehler bei unbekanntem Modell |

### ✅ Erledigte Schritte:
1. ~~**ClaimMiner robuster machen**~~ - `_parse_json_robust` mit Regex-Fallbacks
2. ~~**Editor-Prompt schärfen**~~ - ClaimRegister + Quellen-Snippets + Issue-Typ `hallucination`
3. ~~**Artikellänge fixen**~~ - FORMAT_SPECS mit `words_min`/`words_max` + `min_claims`

### ✅ Halluzinations-Check (Implementiert!)

Der Editorial Review wurde erweitert:

**Input:**
- Artikel
- ClaimRegister mit allen Claims  
- Quellen-Snippets (Titel + URL + Kernaussage)

**Prompt enthält:**
> "Prüfe: Welche Faktenbehauptungen im Artikel haben KEINE Quellenreferenz [X]? → type='hallucination'"

**Issue-Typ im JSON:**
```json
{
  "type": "hallucination",
  "description": "Aussage X hat keine Quellenreferenz",
  "location": "Abschnitt Y, Satz Z",
  "suggested_action": "remove|research"
}
```

**Verhalten:**
- `suggested_action: "remove"` → Reviser entfernt die Passage (Standard!)
- `suggested_action: "research"` → GapRetriever sucht Quelle, dann Reviser ergänzt

---

## 🟠 Issues aus Log-Analyse (25.01.2026)

Identifizierte Probleme bei der kritischen Durchsicht des Session-Logs.

### Bereits gefixt ✅

| Status | Issue | Beschreibung | Fix |
|--------|-------|--------------|-----|
| ✅ | **Irrelevante Quellen im Literaturverzeichnis** | Alle recherchierten Quellen wurden aufgenommen, auch nicht verwendete | `_add_bibliography` filtert jetzt nach `[X]`-Referenzen im Text |
| ✅ | **Prozess-Artefakte im Artikel** | Meta-Kommentare wie "(Abschnitt vervollständigt)" im finalen Text | `_polish_article` entfernt Artefakte + Prompt-Fix |
| ✅ | **Tier-Modell-Inkonsistenz** | ClaimMiner nutzt falsches Tier | `tier_mapping` in `_get_model()` mappt korrekt |
| ✅ | **Semantic Scholar nie verwendet** | Tool wird jetzt verwendet | Wird bei akademischen Themen ausgewählt (2+ Logs) |
| ❌ | **Claim Coverage Tracking** | War: "Prüfen ob alle Claims im Artikel" | **Verworfen** - Editor darf Claims entfernen (Halluzinationen)! |

### Offen ⬜

| Status | Issue | Beschreibung | Auswirkung |
|--------|-------|--------------|------------|
| ✅ | ~~Claims verschwinden beim Retrieval~~ | 23→21 Claims | **Korrekt!** A-Claims (Allgemeinwissen) brauchen keine Recherche |
| ⬜ | **Editorial "approved" mit offenen Issues** | verdict="approved" aber issues_count=4 – logisch inkonsistent | Unklar ob Artikel wirklich fertig |
| ⬜ | **GapRetriever Logging unvollständig** | `tool_calls: []` leer, obwohl 13 Quellen gefunden | Debugging/Transparenz eingeschränkt |

### ✅ Artikellänge-Problem (Gelöst!)

| Status | Issue | Beschreibung | Fix |
|--------|-------|--------------|-----|
| ✅ | **Format-Parameter nicht durchgereicht** | FORMAT_SPECS im Orchestrator | `self.format` durchgängig verwendet |
| ✅ | **Nur Mindest-, keine Maximallänge** | `words_min` + `words_max` | Prompts: "zwischen X und Y Wörter" |
| ✅ | **Claim-Anzahl ignoriert Format** | `min_claims` + `min_c_claims` pro Format | ClaimMiner bekommt Format-Parameter |

### ✅ Implementierte FORMAT_SPECS

| Format | Seiten | Wörter | Claims (min) | C-Claims (min) |
|--------|--------|--------|--------------|----------------|
| overview | 4 | 1200-1800 | 6 | 2 |
| article | 8 | 2400-3200 | 10 | 4 |
| report | 12 | 3600-4800 | 15 | 6 |
| deep_dive | 20 | 6000-8000 | 22 | 8 |

---

## 🔧 Legende

- ⬜ Offen
- 🔄 In Arbeit
- ✅ Erledigt
- ❌ Verworfen

---

## 1. Research Tools erweitern

Weitere Tools aus `DEEP_RESEARCH_TOOLS.md` integrieren.

### Phase 1: Quick Wins (kostenlos, einfache APIs)

| Status | Tool | Kategorie | Aufwand |
|--------|------|-----------|---------|
| ✅ | Wikipedia | Knowledge | ~1h |
| ✅ | Google News (gnews) | News | ~1h |
| ✅ | Hacker News | Tech Community | ~30min |
| ✅ | **Semantic Scholar** | Wissenschaft | ~2h |
| ✅ | **arXiv** | Wissenschaft (Preprints) | ~1h |
| ⬜ | Reddit Search | Community/Meinungen | ~1h |

### Phase 2: Business & Recht

| Status | Tool | Kategorie | Aufwand |
|--------|------|-----------|---------|
| ⬜ | OpenCorporates | Unternehmensdaten | ~2h |
| ✅ | **TED API** | EU-Ausschreibungen | ~2h |
| ⬜ | EUR-Lex | EU-Gesetze | ~2h |

### Phase 3: Statistik & Daten

| Status | Tool | Kategorie | Aufwand |
|--------|------|-----------|---------|
| ⬜ | Destatis (GENESIS) | DE-Statistiken | ~3h |
| ⬜ | Eurostat | EU-Statistiken | ~2h |
| ⬜ | World Bank API | Globale Wirtschaftsdaten | ~2h |

### Phase 4: Spezial

| Status | Tool | Kategorie | Aufwand |
|--------|------|-----------|---------|
| ⬜ | Espacenet/DPMA | Patente | ~3h |
| ⬜ | Stack Overflow | Tech Q&A | ~1h |
| ⬜ | YouTube Data API | Video-Metadaten | ~2h |

---

## 2. Workflow-Flexibilisierung

Orchestrator soll komplexere, adaptive Workflows erstellen können.

| Status | Feature | Beschreibung |
|--------|---------|--------------|
| ✅ | Tool pro Runde | Verschiedene Tools pro Recherche-Runde wählbar |
| ✅ | Modell-Empfehlungen | Orchestrator empfiehlt Premium/Budget pro Agent |
| ✅ | **Dynamische Rundenzahl** | 2-3 (simple), 4-5 (medium), 6-8 (complex) |
| ✅ | **Tool-Diversität** | Orchestrator nutzt verschiedene Tools pro Runde (nie 3x gleiches Tool) |
| ✅ | **Smart Editor-Routing** | Editor-Feedback führt zu gezielter Nachrecherche statt nur Writer-Revision |
| ⬜ | Parallele Suchen | Mehrere Tools gleichzeitig pro Runde nutzen |
| ⬜ | Conditional Rounds | Runden nur ausführen wenn Bedingung erfüllt (z.B. "wenn keine Daten → andere Quelle") |
| ⬜ | Tool-Chaining | Output von Tool A als Input für Tool B (z.B. Wikipedia → dann Deep-Dive mit Tavily) |

### Smart Editor-Routing (NEU!) ✅

Der Editor gibt strukturiertes Feedback mit JSON-Verdict. Der Orchestrator entscheidet dynamisch:

```
Editor → Orchestrator entscheidet:
  ├─→ "approved" → Artikel fertig!
  ├─→ "revise" → Writer überarbeitet (Stil/Struktur)
  └─→ "research" → Gezielte Nachrecherche → dann Writer
```

**Features:**
- Editor identifiziert `content_gap` Issues mit konkretem `research_query`
- Orchestrator wählt passendes Tool für Nachrecherche (z.B. "Kosten" → tavily, "Forschung" → semantic_scholar)
- Max. 3 Nachrecherche-Runden pro Editor-Iteration
- Max. 2 Editor-Iterationen (Endlosschleifen-Schutz)
- Frontend zeigt Editor-Verdict visuell an (✅ Genehmigt / ✏️ Überarbeitung / 🔍 Nachrecherche)

---

## 2b. Quellenqualität & -vielfalt ⭐

Mehr und bessere Quellen pro Artikel.

| Status | Feature | Beschreibung |
|--------|---------|--------------|
| ✅ | **Per-Source Truncation** | Kürzt pro Quelle (400 Zeichen) statt gesamt - alle URLs bleiben erhalten |
| ✅ | **Quellen-Tracking** | Researcher dokumentiert jede Quelle einzeln mit URL und Kernfakten |
| ✅ | **Writer Quellenreferenzierung** | Writer zitiert mit [1], [2], ... + Quellenverzeichnis am Ende |
| ✅ | **Truncation-Limit erhöht** | MAX_TOOL_RESULT_CHARS von 1500 auf 2500 erhöht |
| ✅ | **Strukturierter JSON-Output** | Researcher gibt JSON statt Freitext zurück → 100% Quellenerhalt! |
| ⬜ | Quellen-Diversitäts-Score | Nach Recherche prüfen: genug Quellenarten/Domains? Sonst Nachrecherche |
| ⬜ | Domain-Bundles | Vordefinierte Tool-Pakete pro Themenbereich (public_sector_de, academic, tech, business) |
| ⬜ | Min. Quellenanzahl | Konfigurierbare Untergrenze (z.B. MIN_DISTINCT_SOURCES=10) |
| ⬜ | Fallback-Recherche | Bei schwachen/irrelevanten Ergebnissen automatisch Alternativ-Tool oder neue Query |

### Domain-Bundles (Beispiele)

| Bundle | Tools | Anwendung |
|--------|-------|-----------|
| `public_sector_de` | TED API, EUR-Lex, Destatis, Tavily (.gov.de) | Öffentliche Verwaltung Deutschland |
| `academic` | Semantic Scholar, arXiv, Wikipedia | Wissenschaftliche Themen |
| `tech` | Hacker News, Stack Overflow, GitHub | Technologie & Software |
| `business` | OpenCorporates, TED, gnews (Business) | Unternehmen & Wirtschaft |
| `legal_eu` | EUR-Lex, TED, Wikipedia | EU-Recht & Regulierung |

---

## 3. Output-Formate ✅

Verschiedene Artikel-Längen und -Formate sind implementiert!

| Status | Format | Umfang | Beschreibung |
|--------|--------|--------|--------------|
| ✅ | **overview** | ~4 Seiten | Kompakte Übersicht (1200-1800 Wörter) |
| ✅ | **article** | ~8 Seiten | Standard-Fachartikel (2400-3200 Wörter) |
| ✅ | **report** | ~12 Seiten | Ausführlicher Report (3600-4800 Wörter) |
| ✅ | **deep_dive** | ~20 Seiten | Tiefgehende Analyse (6000-8000 Wörter) |
| ⬜ | Executive Summary | ~0,5 Seiten | Kernaussagen in 3-5 Absätzen (noch nicht) |

### Umsetzung ✅

| Status | Task |
|--------|------|
| ✅ | Format-Auswahl im **PromptRefiner** (Frontend) |
| ✅ | Writer-Prompts dynamisch aus FORMAT_SPECS |
| ✅ | Claim-Anzahl an Format gekoppelt (min_claims pro Format) |

---

## 4. 🚀 Epic: Kollaborativer Schreibmodus

**Vision**: Gemeinsames Erarbeiten längerer Werke (Buch, Thesis, Report) mit MAS-Power aber voller Kontrolle durch den Autor.

### Kernidee

Nicht "1 Klick → 15 Seiten", sondern iterativer Prozess:
1. Autor schreibt Abschnitt / stellt Frage
2. MAS recherchiert gezielt
3. Autor integriert/verwirft Ergebnisse
4. Weiter zum nächsten Abschnitt
5. Dokument wächst organisch

### Workflow-Inspiration (Doktorarbeit)

```
1. Einleitung ins Thema
2. Grundlagen erarbeiten
3. Problem identifizieren
4. Anforderungen/Hypothesen aufstellen
5. Stand der Forschung analysieren
6. Forschungslücke feststellen
7. Eigenen Lösungsbeitrag entwickeln
8. Evaluation durchführen
9. Ergebnisse dokumentieren
10. Fazit schreiben
```

### Features

| Status | Feature | Beschreibung |
|--------|---------|--------------|
| ⬜ | Projekt-Modus | Langlebiges Dokument statt One-Shot-Generierung |
| ⬜ | Kapitel-Struktur | Gliederung vorab definieren, Kapitel einzeln bearbeiten |
| ⬜ | Inline-Recherche | Aus dem Editor heraus gezielt recherchieren |
| ⬜ | Quellen-Management | Alle verwendeten Quellen zentral verwalten |
| ⬜ | Versions-History | Änderungen nachvollziehbar |
| ⬜ | Context-Aware Agents | Agenten kennen bereits geschriebene Teile |
| ⬜ | Hypothesen-Tracker | Offene Fragen und Hypothesen verwalten |
| ⬜ | Literatur-Review-Modus | Systematisch Stand der Forschung aufbauen |

### Technische Basis

| Status | Task |
|--------|------|
| ⬜ | Projekt-Datenmodell (JSON/SQLite) |
| ⬜ | Neuer Frontend-Modus "Studio Pro" / "Collaborative" |
| ⬜ | Markdown-Editor mit MAS-Integration |
| ⬜ | Session-übergreifender Kontext für Agenten |
| ⬜ | Export zu Word/PDF mit Formatierung |

---

## 5. Sonstige Verbesserungen

| Status | Feature | Beschreibung |
|--------|---------|--------------|
| ⬜ | Budget-Modelle optimieren | GPT-4o-mini statt GPT-5.1 als echtes Budget |
| ⬜ | Kosten-Tracking in UI | Echtzeit-Anzeige der API-Kosten |
| ⬜ | Recherche parallelisieren | Runden gleichzeitig statt sequenziell |
| ⬜ | Quellen im Artikel | Alle Recherche-URLs automatisch zitieren |
| ⬜ | Artikel-Templates | Vorlagen für verschiedene Dokumenttypen |
| ⬜ | Export-Formate | PDF, Word, HTML zusätzlich zu Markdown |

---

## 📅 Changelog

| Datum | Änderung |
|-------|----------|
| 2026-01-18 | Backlog erstellt |
| 2026-01-18 | Tool-Registry implementiert (Wikipedia, gnews, HN) |
| 2026-01-18 | Planungsmodus mit Tool- und Modell-Empfehlungen |
| 2026-01-18 | Neuer Abschnitt "Quellenqualität & -vielfalt" hinzugefügt |
| 2026-01-18 | **Quellenqualität verbessert:** Per-Source Truncation, Quellen-Tracking, Writer-Referenzierung |
| 2026-01-18 | **100% Quellenerhalt:** Researcher gibt strukturiertes JSON statt Freitext zurück |
| 2026-01-18 | **Dynamische Rundenzahl:** 2-8 Runden je nach Komplexität (statt fix 5) |
| 2026-01-18 | **Tool-Diversität:** Orchestrator nutzt verschiedene Tools pro Runde |
| 2026-01-18 | **Neues Tool:** Semantic Scholar für wissenschaftliche Paper (200M+ Papers) |
| 2026-01-18 | **Neues Tool:** arXiv für Preprints (ML, KI, CS, Physik) |
| 2026-01-18 | **Neues Tool:** TED API für EU-Ausschreibungen (perfekt für Verwaltung!) |
| 2026-01-18 | **🚀 Smart Editor-Routing:** Editor-Feedback führt zu gezielter Nachrecherche statt nur Writer-Revision |
| 2026-01-25 | **✅ Fix:** Literaturverzeichnis filtert jetzt irrelevante Quellen (nur referenzierte aufnehmen) |
| 2026-01-25 | **✅ Fix:** Prozess-Artefakte werden aus Artikel entfernt (`_polish_article`) |
| 2026-01-25 | **📋 Log-Analyse:** 7 neue Issues identifiziert (Tier-Inkonsistenz, Artikellänge, Tool-Auswahl, etc.) |
| 2026-01-27 | **🎉 Evidence-Gated Flow komplett:** 8-Phasen Workflow produktiv |
| 2026-01-27 | **✅ ClaimMiner JSON-Parsing:** `_parse_json_robust` mit Fallbacks |
| 2026-01-27 | **✅ Halluzinations-Check:** Editor prüft explizit auf unbelegt Fakten |
| 2026-01-27 | **✅ FORMAT_SPECS:** 4 Formate (overview, article, report, deep_dive) mit Wort-/Claim-Limits |
| 2026-01-27 | **✅ PromptRefiner:** Frontend-Feature zur Prompt-Optimierung vor Generierung |
| 2026-01-27 | **✅ Multi-LLM:** Anthropic, OpenAI, Google Gemini integriert |
| 2026-01-27 | **✅ Tier-Mapping:** `_get_model()` mappt Agenten korrekt auf Tiers |
| 2026-01-27 | **❌ Claim Coverage:** Verworfen - Editor darf Claims entfernen (by design) |
| 2026-01-27 | **📋 Backlog-Update:** 15 Items abgehakt/verworfen! |

---

*Zuletzt aktualisiert: 27.01.2026*
