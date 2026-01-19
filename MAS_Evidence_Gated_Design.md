# MAS Research & Writing System – Evidence‑Gated Design (High‑Quality Target)

> Ziel: Aus einer Kernfrage ein hochwertiges, zitierfähiges 10–15‑seitiges Paper erzeugen – **mit kontrollierter Recherche, nachvollziehbarer Evidenzkette und reproduzierbarer Qualität**.  
> Fokus: **Qualität vor Implementierungsaufwand** (Tooling/Änderungsaufwand bewusst ignoriert).

---

## 1. Leitprinzipien

### 1.1 Evidence‑Gated statt Search‑First / Knowledge‑First
Das System schreibt nicht „frei“ und recherchiert auch nicht „blind“. Es arbeitet **claim‑getrieben**:

- **Claims** (prüfbare Aussagen) werden explizit erzeugt, klassifiziert und mit Evidenzanforderungen versehen.
- **Retrieval** wird nur dann ausgeführt, wenn ein Claim es erfordert.
- **Writing** darf nur Claims verwenden, die im Claim‑Register existieren.
- **Editing** prüft Claim‑Abdeckung und Evidenzqualität, nicht „Textgefühl“.

### 1.2 Stop‑Conditions und Budget‑Disziplin sind Qualitätsfeatures
Hohe Qualität entsteht durch **gezielte** Recherche und das Beenden, wenn Evidenz ausreichend ist.  
Wichtig ist nicht „viele Quellen“, sondern **geeignete** Quellen pro Claim (Evidenzklasse + Unabhängigkeit).

### 1.3 Trennung von Rollen
Rollen sind nicht kosmetisch, sondern erzwingen unterschiedliche Optimierungsziele:

- **Planner**: zerlegt, normalisiert, definiert Scope.
- **Claim Miner**: erzeugt Claim‑Register.
- **Retriever**: beschafft Evidenz nach Regeln.
- **Evidence Rater**: bewertet Quellenqualität.
- **Writer**: schreibt strikt „claim‑bounded“.
- **Editor**: prüft Claim‑Coverage, Konsistenz, Stil.
- **Verifier**: prüft Halluzinationsoberfläche und Quellenbezug final.

---

## 2. Systemarchitektur (Übersicht)

### 2.1 Pipeline (Phasen)

1. **Query Normalization & Scope**
2. **Outline & Claim Mining**
3. **Evidence Planning (Tickets)**
4. **Targeted Retrieval + Evidence Packaging**
5. **Draft Writing (Inline Evidence Anchors)**
6. **Editorial Review (Claim Coverage & Consistency)**
7. **Gap Loop (nur für offene C‑Claims)**
8. **Final Verification & Bibliography Build**
9. **Publication Packaging (PDF/MD/Docx optional)**

### 2.2 Datenobjekte (Artefakte)

- `QuestionBrief`
- `TermMap` (Synonyme, Ausschlüsse, Kanonische Begriffe)
- `Outline`
- `ClaimRegister` (Claims + Evidenzklasse + Tickets)
- `EvidencePack` (pro Claim: Quellen + Extrakte + Bewertung)
- `Draft` (mit Claim‑Anchors)
- `ReviewReport` (Coverage, Widersprüche, neue Claims)
- `FinalPaper` (Text + Literaturverzeichnis)

---

## 3. Phase 1 – Query Normalization & Scope

### 3.1 Ziele
- Ambiguität reduzieren (Terminologie, Produktnamen, Versionen).
- Scope definieren (was ist in/out).
- „Freshness“-Erfordernisse festlegen (Stand‑Datum, zeitkritische Fakten).

### 3.2 Output: `QuestionBrief` + `TermMap`

**QuestionBrief**
- Kernfrage (präzisiert)
- Zielpublikum, Ton (z. B. Fachpapier, Management Summary)
- Tiefe (10–15 Seiten)
- Stand‑Datum
- Zeitkritik (hoch/mittel/niedrig)

**TermMap**
- User‑Term → kanonische Begriffe (1..n)
- Synonyme
- Negative Keywords (zu vermeidende Treffer)
- Verwandte Konzepte (für Recall)
- „Disambiguation Notes“ (z. B. Produkt vs. Feature)

### 3.3 Qualitätsregeln
- Jede kanonische Termgruppe bekommt 3–5 Such‑Varianten.
- Negative Keywords müssen gesetzt werden, wenn es bekannte Verwechslungen gibt.

---

## 4. Phase 2 – Outline & Claim Mining (Herzstück)

### 4.1 Grundidee
Statt „Lücken markieren“ (was oft zu 0 Markierungen führt) erzwingt das System eine **feste Menge an Claims**.

### 4.2 Claim‑Typen
- **Definition Claim**: „X ist …“
- **Mechanism Claim**: „X funktioniert so, dass …“
- **Comparison Claim**: „X unterscheidet sich von Y durch …“
- **Effect Claim**: „X führt typischerweise zu …“
- **Quant Claim**: Zahlen/Prozent/Zeiten/Marktwerte
- **Temporal Claim**: „seit“, „aktuell“, „neu“, „Stand …“
- **Normative Claim**: „sollte“, „empfohlen“, „best practice“ (erfordert Begründung)

### 4.3 Evidenzklassen (A/B/C)
- **A – Stable Background**: Allgemeinwissen, stabil, nicht volatil. *Keine Quelle erforderlich*, optional 1 Standardwerk.
- **B – Source Recommended**: Fachliche Einordnung, definitorische Details, nicht extrem volatil. *1 gute Quelle* reicht.
- **C – Source Mandatory**: Volatile Fakten, Zahlen, aktuelle Ereignisse, strittige Aussagen, rechtliche/produktversionsbezogene Details.  
  *Mind. 2 unabhängige Quellen* oder *Primärquelle + unabhängige Sekundärquelle*.

### 4.4 Output: `Outline` + `ClaimRegister`

**Outline**
- Kapitelstruktur (für 10–15 Seiten)
- Pro Kapitel: Ziel und erwartete Claims

**ClaimRegister**
- Nummerierte Claims (z. B. C‑01 …)
- Claim‑Text (präzise, testbar)
- Claim‑Typ
- Evidenzklasse A/B/C
- Quellenklassen‑Anforderung (Primär/Sekundär/Tertiär)
- Freshness‑Flag (ja/nein) + Stichtag
- Retrieval‑Ticket (Query‑Set + Filter)
- Abhängigkeiten (Claim baut auf Claim X auf)

### 4.5 Mindestanforderungen (Zwangsmechanik)
- Mindestens **12–20 Claims** insgesamt (bei 10–15 Seiten: eher 18–30).
- Mindestens **4–8 C‑Claims** (sonst wird „Paper“ zu generisch).
- Jeder B/C‑Claim muss mind. 2 konkrete Suchqueries enthalten.

---

## 5. Phase 3 – Evidence Planning (Tickets)

### 5.1 Ticket‑Struktur
Für jeden B/C‑Claim entsteht ein `RetrievalTicket`:

- `claim_id`
- `queries[]` (mit Synonymen/Sprachvarianten)
- `preferred_domains[]` (optional)
- `excluded_domains[]` (optional)
- `evidence_requirements`
  - min_sources
  - independence_rule
  - primary_required (bool)
  - recency_days (wenn Freshness)
- `acceptance_criteria`
  - „Welche Art Textstelle muss die Quelle enthalten?“

### 5.2 Source‑Priorisierung (Evidenzklassen)
1. **Primär**: Hersteller/Standard/Norm/Behördenquelle (für „ist/hat/enthält“)
2. **Sekundär**: etablierte Fachmedien, Institute, Peer‑Review (für Einordnung, Vergleich)
3. **Tertiär**: HN/Reddit/Blogs (nur Praxisindikatoren, niemals alleinige Evidenz)

---

## 6. Phase 4 – Targeted Retrieval & Evidence Packaging

### 6.1 Retrieval‑Strategie
- Pro Ticket: iteriere Queries, bis Akzeptanzkriterien erfüllt sind.
- **Stop‑Condition**: sobald `min_sources` + `independence_rule` erfüllt sind.
- Harte Obergrenzen:
  - max_sources_per_claim (z. B. 6)
  - max_total_sources (z. B. 40–60, abhängig vom Paper)

### 6.2 Evidence Packaging
Aus jeder Quelle werden extrahiert:
- bibliographische Metadaten
- relevanter Auszug (kurz, paraphrasierend; keine langen Zitate)
- Mapping: welche Passage stützt welchen Claim (1:n möglich)

Output: `EvidencePack` pro Claim.

---

## 7. Phase 5 – Evidence Rating (Quellenbewertung)

### 7.1 Bewertungsdimensionen
- **Authority**: Primärquelle / etablierte Institution / unbekannt
- **Independence**: Hersteller‑nah? PR? Affiliate?
- **Recency**: passt zur Freshness‑Anforderung?
- **Specificity**: belegt genau den Claim oder nur Kontext?
- **Consensus**: bestätigen mehrere Quellen dieselbe Aussage?

### 7.2 Score (Vorschlag)
Skala 0–3 je Dimension; Summenscore 0–15.  
Mindestscore für C‑Claims: z. B. **>=10**.

---

## 8. Phase 6 – Draft Writing (Claim‑Bounded Writing)

### 8.1 Schreibregeln
- Writer darf nur Aussagen machen, die:
  - A‑Claim (stabil) oder
  - B/C‑Claim mit EvidencePack besitzen.
- Jede relevante Aussage wird mit einem **Claim‑Anchor** markiert:
  - Beispiel: „… (C‑07)“
- Keine „neuen“ Fakten ohne Claim‑Register.

### 8.2 Struktur
- Executive Summary (max 1 Seite)
- Hauptteil (Kapitel gem. Outline)
- Implikationen / Empfehlungen (als normative Claims mit Evidenz)
- Limitations (explizit)
- Bibliography

---

## 9. Phase 7 – Editorial Review (Claim Coverage & Consistency)

### 9.1 Review‑Report Inhalte
- **Claim Coverage Rate**
  - Anteil Claims, die im Text genutzt werden (optional)
  - Anteil C‑Claims, die im Text korrekt belegt sind (muss 100% werden)
- **Evidence Sufficiency**
  - pro C‑Claim: erfüllt? ja/nein + warum
- **Contradictions**
  - Quellen widersprechen sich? → markieren
- **New Claims Detection**
  - Aussagen im Text ohne Claim‑Anchor → als „Hallucination Surface“
- **Style / Clarity**
  - erst nach evidenzbasierten Checks

### 9.2 Gap Loop Regeln
Nur wenn:
- C‑Claims „nicht erfüllt“
- oder Widerspruch ungeklärt

Dann:
- neue Tickets erstellen (gezielt)
- kein globales Re‑Search

---

## 10. Phase 8 – Final Verification & Bibliography Build

### 10.1 Final Verification (streng)
- Jede Zahl / jedes „aktuell“ / jeder rechtliche Verweis muss Claim‑ID + EvidencePack haben.
- Prüfen: Zitierfähigkeit (Autor, Datum, Titel, Publisher).
- Prüfen: Vermeidung von überlangen Zitaten (Copyright‑Risiko).

### 10.2 Bibliography
- konsistenter Zitierstil (APA, Chicago oder IEEE – fest wählen)
- Sortierung
- eindeutige Identifikatoren (URL/DOI)

---

## 11. Qualitätsmetriken (operativ)

### 11.1 Kernmetriken (empfohlen)
1. **Claim Coverage Rate (C‑Claims)**  
   Ziel: 100% der C‑Claims im Text belegt.
2. **Independence Score**  
   Ziel: >60% nicht‑Herstellerquellen (je nach Thema).
3. **Retrieval Efficiency**  
   Quellen pro erfülltem C‑Claim: niedrig (z. B. 2–4).
4. **Hallucination Surface**  
   Aussagen ohne Claim‑Anchor: nahe 0.
5. **Recency Compliance**  
   Freshness‑Claims: 100% erfüllen Stichtag/Recency.

### 11.2 Akzeptanzkriterien für „High Quality“
- 0 ungeankerte Fakten
- 0 unbelegte C‑Claims
- 0 ungeklärte Widersprüche (oder explizit als „uneinheitliche Quellenlage“ dokumentiert)
- Bibliography vollständig, konsistent, zitierfähig

---

## 12. Prompt‑/Schema‑Spezifikation (für robuste Orchestrierung)

### 12.1 ClaimRegister JSON Schema (Vorschlag)
```json
{
  "question_brief": {
    "core_question": "...",
    "audience": "...",
    "tone": "...",
    "as_of_date": "YYYY-MM-DD",
    "freshness_priority": "high|medium|low"
  },
  "term_map": {
    "canonical_terms": ["..."],
    "synonyms": ["..."],
    "negative_keywords": ["..."],
    "disambiguation_notes": ["..."]
  },
  "outline": [
    {"section": "1 ...", "goal": "...", "expected_claim_ids": ["C-01","C-02"]}
  ],
  "claims": [
    {
      "claim_id": "C-01",
      "claim_text": "...",
      "claim_type": "definition|mechanism|comparison|effect|quant|temporal|normative",
      "evidence_class": "A|B|C",
      "freshness_required": true,
      "recency_days": 90,
      "required_source_classes": ["primary","secondary"],
      "min_sources": 2,
      "independence_rule": "different_publishers",
      "retrieval_ticket": {
        "queries": ["...", "..."],
        "preferred_domains": [],
        "excluded_domains": []
      }
    }
  ]
}
```

### 12.2 EvidencePack JSON Schema (Vorschlag)
```json
{
  "claim_id": "C-01",
  "sources": [
    {
      "source_id": "S-001",
      "title": "...",
      "publisher": "...",
      "author": "...",
      "date": "YYYY-MM-DD",
      "url": "...",
      "source_class": "primary|secondary|tertiary",
      "extract": "paraphrased excerpt relevant to claim",
      "supports": ["C-01"],
      "ratings": {
        "authority": 0,
        "independence": 0,
        "recency": 0,
        "specificity": 0,
        "consensus": 0,
        "total": 0
      }
    }
  ],
  "status": "fulfilled|insufficient|conflict",
  "notes": "..."
}
```

---

## 13. Anti‑Patterns (explizit vermeiden)

1. **Search‑First Global Crawl**  
   Führt zu Materialflut, steigenden Kosten und schlechterer Synthese.
2. **„Markiere Lücken“ ohne Zwang**  
   Führt häufig zu 0 Markierungen (Modelle glätten Unsicherheit).
3. **Quellenmenge als Qualitätsproxy**  
   Qualität entsteht durch Evidenzpassung, nicht durch Anzahl.
4. **Reddit/HN als Evidenz**  
   Nur als Praxisindikator; nie alleinige Stütze.
5. **Synthese ohne Claim‑Kontrolle**  
   Erhöht Halluzinationsoberfläche drastisch.

---

## 14. Empfohlene Modell-/Agentenbelegung (prinzipiell)

- **Planner / TermMap**: Modell mit guter Disambiguation und Strukturierungsfähigkeit.
- **Claim Miner / Editor**: Modell mit starker Kritikfähigkeit.
- **Retriever**: Tool‑Agent (Search + Scrape) + kurzes Modell für Extrakte.
- **Writer**: Modell mit starker Schreibqualität.
- **Verifier**: kritisches Modell, strikt auf Claim‑Anchors.

Hinweis: Multi‑Model ist hilfreich, aber sekundär. Primär ist das Protokoll.

---

## 15. Ergebnisartefakte (Deliverables)

- `paper.md` (mit Claim‑Anchors entfernt oder optional als Fußnoten)
- `claim_register.json`
- `evidence_pack/` (pro Claim eine Datei)
- `review_report.md`
- `bibliography.bib` oder `references.md`

---

## 16. Kurzfassung: Was dieses Design löst

- **Das „Goldilocks“-Problem**: Wissensnutzung vs. Recherche wird über Evidenzklassen entschieden.
- **Follow‑Up‑Recherche**: erfolgt nur über offene C‑Claims, nicht über diffuse „Lücken“.
- **Quellenqualität**: wird pro Claim bewertet, nicht pauschal gesammelt.
- **Reproduzierbarkeit**: Claim‑Register + EvidencePack machen das Ergebnis nachprüfbar.
- **Kostenkontrolle**: Stop‑Conditions verhindern Recherche‑Eskalation, ohne Qualität zu verlieren.

---

*Ende.*
