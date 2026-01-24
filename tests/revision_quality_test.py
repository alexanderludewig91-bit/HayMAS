#!/usr/bin/env python3
"""
Revision Quality Test - Testet die Qualität des Revisionsprompts
Vergleicht verschiedene Revision-Szenarien und misst ob Änderungen gezielt sind.
"""

import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional

# Projektroot zum Path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import OPENAI_API_KEY

# Mock-Artikel für Tests (realistischer kurzer Artikel)
MOCK_ARTICLE = """# Einführung in Cloud Computing für die öffentliche Verwaltung

## Executive Summary

Cloud Computing bietet der öffentlichen Verwaltung erhebliche Vorteile in Bezug auf Kosteneffizienz, Skalierbarkeit und Modernisierung der IT-Infrastruktur [1]. Diese Übersicht analysiert die wichtigsten Aspekte und Herausforderungen.

## 1. Grundlagen des Cloud Computing

Cloud Computing bezeichnet die Bereitstellung von IT-Ressourcen über das Internet [2]. Die drei Hauptmodelle sind Infrastructure as a Service (IaaS), Platform as a Service (PaaS) und Software as a Service (SaaS) [3].

### 1.1 Vorteile für Behörden

Die Vorteile umfassen reduzierte Infrastrukturkosten, erhöhte Flexibilität und verbesserte Zusammenarbeit zwischen Abteilungen [4]. Besonders relevant ist die Möglichkeit zur schnellen Skalierung bei Bedarfsspitzen.

## 2. Sicherheitsaspekte

Datenschutz und Compliance sind zentrale Herausforderungen [5]. Die DSGVO stellt besondere Anforderungen an die Verarbeitung personenbezogener Daten in der Cloud.

## 3. Fazit

Cloud Computing ist ein wichtiger Baustein der Verwaltungsdigitalisierung, erfordert aber sorgfältige Planung und Umsetzung.

## Quellenverzeichnis

[1] Bundesministerium des Innern: Cloud-Strategie der Bundesverwaltung, 2024
[2] Bitkom: Cloud Computing Leitfaden, 2023
[3] NIST: Definition of Cloud Computing, 2011
[4] Gartner: Government Cloud Adoption Report, 2024
[5] BSI: Cloud Computing Grundlagen, 2023
"""

@dataclass
class TestIssue:
    type: str
    severity: str
    description: str
    suggested_action: str

@dataclass
class TestVerdict:
    verdict: str
    confidence: float
    summary: str
    issues: List[TestIssue]

@dataclass
class RevisionResult:
    scenario: str
    original_words: int
    revised_words: int
    word_change_percent: float
    tokens_used: int
    cost_usd: float
    revision_focused: bool  # Subjektive Bewertung ob gezielt
    notes: str

def create_test_scenarios() -> List[tuple]:
    """Erstellt verschiedene Test-Szenarien mit unterschiedlichen Issues."""
    
    scenarios = [
        # Szenario 1: Nur Quellenprobleme
        (
            "sources_only",
            TestVerdict(
                verdict="revise",
                confidence=0.7,
                summary="Der Artikel hat gute Struktur, aber einige Aussagen sind nicht belegt.",
                issues=[
                    TestIssue(
                        type="sources",
                        severity="medium",
                        description="In Abschnitt 1.1 fehlen Quellenverweise für die genannten Vorteile",
                        suggested_action="Füge Quellenverweise [X] für die Aussagen zu Kosteneinsparungen hinzu"
                    )
                ]
            )
        ),
        
        # Szenario 2: Strukturproblem
        (
            "structure_only",
            TestVerdict(
                verdict="revise",
                confidence=0.75,
                summary="Dem Artikel fehlt ein wichtiger Abschnitt.",
                issues=[
                    TestIssue(
                        type="structure",
                        severity="high",
                        description="Es fehlt ein Abschnitt zu 'Limitationen und Risiken'",
                        suggested_action="Ergänze einen Abschnitt 2.1 'Risiken und Limitationen' nach den Sicherheitsaspekten"
                    )
                ]
            )
        ),
        
        # Szenario 3: Inhaltslücke
        (
            "content_gap",
            TestVerdict(
                verdict="revise",
                confidence=0.65,
                summary="Ein wichtiges Thema wird nicht ausreichend behandelt.",
                issues=[
                    TestIssue(
                        type="content_gap",
                        severity="medium",
                        description="Das Thema 'Sovereign Cloud' und deutsche Cloud-Anbieter fehlt komplett",
                        suggested_action="Erweitere Abschnitt 2 um einen Unterabschnitt zu deutschen/europäischen Cloud-Anbietern"
                    )
                ]
            )
        ),
        
        # Szenario 4: Multiple Issues (realistisch)
        (
            "multiple_issues",
            TestVerdict(
                verdict="revise",
                confidence=0.6,
                summary="Mehrere kleinere Verbesserungen nötig.",
                issues=[
                    TestIssue(
                        type="sources",
                        severity="low",
                        description="Aussage zu 'schneller Skalierung' ohne Beleg",
                        suggested_action="Quellenangabe ergänzen"
                    ),
                    TestIssue(
                        type="consistency",
                        severity="medium",
                        description="Executive Summary erwähnt 'Kosteneffizienz', aber der Haupttext geht nicht darauf ein",
                        suggested_action="Im Haupttext konkrete Zahlen oder Beispiele zu Kosteneffizienz ergänzen"
                    )
                ]
            )
        ),
        
        # Szenario 5: Länge explizit genannt
        (
            "length_issue",
            TestVerdict(
                verdict="revise",
                confidence=0.7,
                summary="Der Abschnitt zu Sicherheit ist zu oberflächlich.",
                issues=[
                    TestIssue(
                        type="length",
                        severity="medium",
                        description="Abschnitt 2 (Sicherheitsaspekte) ist mit nur 2 Sätzen zu kurz",
                        suggested_action="Erweitere den Sicherheitsabschnitt um konkrete Maßnahmen und BSI-Empfehlungen"
                    )
                ]
            )
        )
    ]
    
    return scenarios


def run_revision_test(scenario_name: str, verdict: TestVerdict, article: str) -> RevisionResult:
    """Führt einen einzelnen Revisionstest durch."""
    
    from openai import OpenAI
    
    # Issues formatieren
    issues_text = ""
    for issue in verdict.issues:
        issues_text += f"- [{issue.severity.upper()}] {issue.type}: {issue.description}\n"
        issues_text += f"  Aktion: {issue.suggested_action}\n"
    
    current_word_count = len(article.split())
    
    # Der NEUE qualitätsfokussierte Prompt
    prompt = f"""Du bist ein erfahrener wissenschaftlicher Lektor. Deine Aufgabe ist eine GEZIELTE ÜBERARBEITUNG.

# EDITOR-FEEDBACK
{verdict.summary}

## Zu behebende Probleme:
{issues_text}

# AKTUELLER ARTIKEL
{article}

# ÜBERARBEITUNGSANLEITUNG

## Dein Auftrag
Behebe EXAKT die oben genannten Probleme. Nicht mehr, nicht weniger.

## Issue-spezifische Maßnahmen
- "sources": Füge an den kritisierten Stellen fehlende Quellenverweise [X] ein
- "structure": Ergänze konkret die fehlenden Abschnitte (z.B. Executive Summary, Limitations)
- "content_gap": Vertiefe GENAU die genannten Themen mit den neuen Quellen
- "consistency": Korrigiere PRÄZISE die genannten Widersprüche
- "length": Erweitere die KONKRET kritisierten dünnen Passagen

## Qualitätsprinzipien
1. CHIRURGISCHE PRÄZISION: Ändere nur, was kritisiert wurde
2. KONTEXT BEWAHREN: Bestehende gute Passagen bleiben unverändert
3. QUELLENINTEGRITÄT: Alle [X]-Verweise müssen erhalten bleiben
4. VOLLSTÄNDIGKEIT: Gib den GESAMTEN Artikel zurück (nicht nur Änderungen)

## WICHTIG
- Keine proaktiven "Verbesserungen" an Stellen ohne Kritik
- Kein Fülltext - jede Ergänzung muss einen Issue adressieren
- Der wissenschaftliche Ton bleibt durchgehend sachlich

ÜBERARBEITETER ARTIKEL:"""

    # API-Aufruf
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Günstigeres Modell für Tests
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=4000
    )
    
    revised_article = response.choices[0].message.content
    revised_words = len(revised_article.split()) if revised_article else 0
    
    tokens_input = response.usage.prompt_tokens
    tokens_output = response.usage.completion_tokens
    total_tokens = tokens_input + tokens_output
    
    # Kosten für gpt-4o-mini: $0.15/1M input, $0.60/1M output
    cost = (tokens_input * 0.00015 / 1000) + (tokens_output * 0.0006 / 1000)
    
    word_change = ((revised_words - current_word_count) / current_word_count) * 100
    
    # Einfache Heuristik für "fokussierte Revision"
    # Wenn Änderung < 30% und nicht negativ bei non-length issues
    if "length" in [i.type for i in verdict.issues]:
        focused = revised_words > current_word_count  # Sollte länger sein
    else:
        focused = abs(word_change) < 30  # Sollte nicht zu viel ändern
    
    return RevisionResult(
        scenario=scenario_name,
        original_words=current_word_count,
        revised_words=revised_words,
        word_change_percent=round(word_change, 1),
        tokens_used=total_tokens,
        cost_usd=round(cost, 4),
        revision_focused=focused,
        notes=f"Issues: {[i.type for i in verdict.issues]}"
    )


def run_all_tests():
    """Führt alle Revisionstests durch und speichert Ergebnisse."""
    
    print("=" * 60)
    print("REVISION QUALITY TEST")
    print("=" * 60)
    print(f"Testzeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Artikel-Länge: {len(MOCK_ARTICLE.split())} Wörter")
    print("=" * 60)
    
    scenarios = create_test_scenarios()
    results = []
    
    for scenario_name, verdict in scenarios:
        print(f"\n🧪 Test: {scenario_name}")
        print(f"   Issues: {[i.type for i in verdict.issues]}")
        
        try:
            result = run_revision_test(scenario_name, verdict, MOCK_ARTICLE)
            results.append(result)
            
            status = "✅" if result.revision_focused else "⚠️"
            print(f"   {status} Wörter: {result.original_words} → {result.revised_words} ({result.word_change_percent:+.1f}%)")
            print(f"   💰 Kosten: ${result.cost_usd:.4f} ({result.tokens_used} tokens)")
            
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
            results.append(RevisionResult(
                scenario=scenario_name,
                original_words=len(MOCK_ARTICLE.split()),
                revised_words=0,
                word_change_percent=0,
                tokens_used=0,
                cost_usd=0,
                revision_focused=False,
                notes=f"ERROR: {str(e)}"
            ))
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    
    total_cost = sum(r.cost_usd for r in results)
    focused_count = sum(1 for r in results if r.revision_focused)
    
    print(f"Tests durchgeführt: {len(results)}")
    print(f"Fokussierte Revisionen: {focused_count}/{len(results)}")
    print(f"Gesamtkosten: ${total_cost:.4f}")
    
    # Detailtabelle
    print("\n┌─────────────────────┬────────┬────────┬──────────┬─────────┐")
    print("│ Szenario            │ Vorher │ Nachher│ Änderung │ Fokus?  │")
    print("├─────────────────────┼────────┼────────┼──────────┼─────────┤")
    for r in results:
        status = "✅" if r.revision_focused else "❌"
        print(f"│ {r.scenario:<19} │ {r.original_words:>6} │ {r.revised_words:>6} │ {r.word_change_percent:>+7.1f}% │ {status:^7} │")
    print("└─────────────────────┴────────┴────────┴──────────┴─────────┘")
    
    # Ergebnisse speichern
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tests/results/revision_quality_{timestamp}.json"
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "prompt_version": "quality_focused_v1",
        "mock_article_words": len(MOCK_ARTICLE.split()),
        "total_cost_usd": total_cost,
        "focused_ratio": f"{focused_count}/{len(results)}",
        "results": [asdict(r) for r in results]
    }
    
    os.makedirs("tests/results", exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Ergebnisse gespeichert: {results_file}")
    
    return results


if __name__ == "__main__":
    run_all_tests()
