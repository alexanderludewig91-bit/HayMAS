#!/usr/bin/env python3
"""
Prompt-Sensitivitäts-Analyse

Testet, wie verschiedene Prompt-Formulierungen die QuestionBrief-Parameter beeinflussen.
Läuft nur Phase 1 (QueryNormalizer) durch.
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evidence_gated.agents.query_normalizer import QueryNormalizerAgent
from agents.base_agent import EventType


# Test-Prompts
TEST_PROMPTS = [
    {
        "id": "T1",
        "prompt": "Übersicht e-Aktensysteme Deutschland",
        "description": "Baseline 'Übersicht'"
    },
    {
        "id": "T2", 
        "prompt": "Artikel über e-Aktensysteme Deutschland",
        "description": "Unterschied zu Übersicht?"
    },
    {
        "id": "T3",
        "prompt": "Expertenbericht e-Aktensysteme Deutschland",
        "description": "Das 'Magic Word'?"
    },
    {
        "id": "T4",
        "prompt": "Analyse der e-Aktensysteme Deutschland",
        "description": "Wissenschaftlicher?"
    },
    {
        "id": "T5",
        "prompt": "Deep-Dive e-Aktensysteme Deutschland",
        "description": "Mehr Seiten?"
    },
    {
        "id": "T6",
        "prompt": "Kurze Übersicht e-Aktensysteme Deutschland",
        "description": "Weniger Seiten?"
    },
    {
        "id": "T7",
        "prompt": "Ausführlicher Expertenbericht e-Aktensysteme Deutschland",
        "description": "Mehr Seiten?"
    },
    {
        "id": "T8",
        "prompt": "Expertenbericht e-Aktensysteme für IT-Entscheider",
        "description": "Zielgruppe = Management?"
    },
]


def run_single_test(prompt: str, test_id: str) -> Dict[str, Any]:
    """Führt einen einzelnen Test durch und gibt das QuestionBrief zurück."""
    print(f"\n{'='*60}")
    print(f"🧪 Test {test_id}: {prompt[:50]}...")
    print(f"{'='*60}")
    
    agent = QueryNormalizerAgent(tier="premium")
    
    result = None
    for event in agent.normalize(prompt):
        if event.event_type == EventType.STATUS:
            print(f"  📍 {event.content}")
        elif event.event_type == EventType.ERROR:
            print(f"  ❌ {event.content}")
    
    # Das Ergebnis kommt als Return-Wert vom Generator
    # Wir müssen den Generator nochmal durchlaufen um den Return zu bekommen
    agent2 = QueryNormalizerAgent(tier="premium")
    gen = agent2.normalize(prompt)
    
    try:
        while True:
            event = next(gen)
    except StopIteration as e:
        result = e.value
    
    if result and "question_brief" in result:
        qb = result["question_brief"]
        return {
            "audience": qb.audience,
            "tone": qb.tone,
            "target_pages": qb.target_pages,
            "freshness_priority": qb.freshness_priority,
            "scope_in": qb.scope_in,
            "scope_out": qb.scope_out,
            "core_question": qb.core_question
        }
    else:
        return {"error": "Kein QuestionBrief erhalten"}


def run_all_tests() -> List[Dict[str, Any]]:
    """Führt alle Tests durch und sammelt die Ergebnisse."""
    results = []
    
    for test in TEST_PROMPTS:
        try:
            qb_result = run_single_test(test["prompt"], test["id"])
            results.append({
                "test_id": test["id"],
                "prompt": test["prompt"],
                "description": test["description"],
                "question_brief": qb_result
            })
            print(f"\n  ✅ Ergebnis:")
            print(f"     audience: {qb_result.get('audience', '?')}")
            print(f"     tone: {qb_result.get('tone', '?')}")
            print(f"     target_pages: {qb_result.get('target_pages', '?')}")
            print(f"     freshness: {qb_result.get('freshness_priority', '?')}")
        except Exception as e:
            print(f"  ❌ Fehler: {e}")
            results.append({
                "test_id": test["id"],
                "prompt": test["prompt"],
                "description": test["description"],
                "error": str(e)
            })
    
    return results


def print_comparison_table(results: List[Dict[str, Any]]):
    """Druckt eine Vergleichstabelle."""
    print("\n" + "="*80)
    print("📊 VERGLEICHSTABELLE")
    print("="*80)
    
    # Header
    print(f"{'ID':<4} {'Prompt':<45} {'Audience':<15} {'Tone':<15} {'Pages':<6}")
    print("-"*80)
    
    for r in results:
        if "error" in r:
            print(f"{r['test_id']:<4} {r['prompt'][:43]:<45} ERROR")
        else:
            qb = r["question_brief"]
            print(f"{r['test_id']:<4} {r['prompt'][:43]:<45} {qb.get('audience', '?'):<15} {qb.get('tone', '?'):<15} {str(qb.get('target_pages', '?')):<6}")
    
    print("="*80)


def save_results(results: List[Dict[str, Any]]):
    """Speichert die Ergebnisse als JSON."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prompt_sensitivity_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "test_count": len(results),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Ergebnisse gespeichert: {filepath}")
    return filepath


def main():
    print("🧪 Prompt-Sensitivitäts-Analyse")
    print("="*60)
    print(f"Tests: {len(TEST_PROMPTS)}")
    print(f"Ziel: Verstehen wie Prompt-Formulierung QuestionBrief beeinflusst")
    print("="*60)
    
    results = run_all_tests()
    
    print_comparison_table(results)
    
    filepath = save_results(results)
    
    print("\n✅ Analyse abgeschlossen!")
    print(f"   Ergebnisse: {filepath}")


if __name__ == "__main__":
    main()
