#!/usr/bin/env python3
"""
Gemini vs Claude Vergleichstest
Testet beide Modelle mit identischem Prompt für Claim Mining.
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY

# Test-Prompt für Claim Mining (vereinfacht)
TEST_TOPIC = "Low-Code-Plattformen in der öffentlichen Verwaltung Deutschlands"

CLAIM_MINING_PROMPT = f"""Du bist ein Experte für wissenschaftliche Analyse. 

AUFGABE: Erstelle für das Thema "{TEST_TOPIC}" eine Liste von 8-10 Kernaussagen (Claims), die in einem Fachartikel belegt werden müssten.

Für jeden Claim:
1. Formuliere die Aussage präzise
2. Klassifiziere den Typ: DEFINITION, MECHANISM, COMPARISON, EFFECT, QUANT (Zahlen), TEMPORAL (Zeit), NORMATIVE (Bewertung)
3. Bestimme die Evidence-Class:
   - A: Allgemeinwissen, kein Beleg nötig
   - B: Quelle empfohlen
   - C: Quelle ZWINGEND (kontrovers/spezifisch)

Antworte NUR mit validem JSON in diesem Format:
{{
  "claims": [
    {{
      "id": "C-01",
      "statement": "...",
      "type": "DEFINITION|MECHANISM|...",
      "evidence_class": "A|B|C",
      "why_this_class": "kurze Begründung"
    }}
  ]
}}
"""


def test_api_connection():
    """Testet ob alle APIs erreichbar sind."""
    print("\n" + "=" * 60)
    print("1. API-VERBINDUNGSTEST")
    print("=" * 60)
    
    results = {}
    
    # Anthropic
    print("\n🔍 Teste Anthropic (Claude)...")
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Versuche verschiedene Modelle
    claude_models = ["claude-sonnet-4-5-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
    for model_name in claude_models:
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=50,
                messages=[{"role": "user", "content": "Antworte mit 'OK'"}]
            )
            print(f"   ✅ {model_name} funktioniert!")
            results["claude"] = True
            results["claude_model"] = model_name
            break
        except Exception as e:
            if "404" in str(e):
                continue
            print(f"   ⚠️ {model_name}: {str(e)[:50]}")
    else:
        print(f"   ❌ Kein Claude-Modell verfügbar!")
        results["claude"] = False
    
    # Gemini Flash (Budget)
    print("\n🔍 Teste Gemini 2.5 Flash (Budget)...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Antworte mit 'OK'")
        print(f"   ✅ Gemini 2.5 Flash funktioniert! Response: {response.text[:20]}")
        results["gemini_flash"] = True
    except Exception as e:
        print(f"   ❌ Gemini Flash Fehler: {e}")
        results["gemini_flash"] = False
    
    # Gemini 3 Pro (Premium - das neueste!)
    print("\n🔍 Teste Gemini 3 Pro (Premium)...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content("Antworte mit 'OK'")
        print(f"   ✅ Gemini 3 Pro funktioniert! Response: {response.text[:20]}")
        results["gemini_pro"] = True
    except Exception as e:
        print(f"   ❌ Gemini 3 Pro Fehler: {e}")
        results["gemini_pro"] = False
    
    return results


def test_claim_mining_claude(model_name="claude-3-5-sonnet-20241022"):
    """Claim Mining mit Claude."""
    from anthropic import Anthropic
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    start = time.time()
    response = client.messages.create(
        model=model_name,
        max_tokens=2000,
        messages=[{"role": "user", "content": CLAIM_MINING_PROMPT}]
    )
    duration = time.time() - start
    
    return {
        "provider": "Anthropic",
        "model": model_name,
        "response": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "duration_sec": round(duration, 2),
        # Claude 3.5 Sonnet: $3/1M input, $15/1M output
        "cost_usd": round((response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000, 4)
    }


def test_claim_mining_gemini_flash():
    """Claim Mining mit Gemini 2.5 Flash (Budget)."""
    import google.generativeai as genai
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    start = time.time()
    response = model.generate_content(CLAIM_MINING_PROMPT)
    duration = time.time() - start
    
    # Token-Zählung bei Gemini
    input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
    output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
    
    return {
        "provider": "Google",
        "model": "gemini-2.5-flash",
        "response": response.text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_sec": round(duration, 2),
        # Gemini 2.5 Flash: $0.15/1M input, $0.60/1M output
        "cost_usd": round((input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000, 6)
    }


def test_claim_mining_gemini_pro():
    """Claim Mining mit Gemini 3 Pro (Premium - das neueste!)."""
    import google.generativeai as genai
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-pro-preview')
    
    start = time.time()
    response = model.generate_content(CLAIM_MINING_PROMPT)
    duration = time.time() - start
    
    input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
    output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
    
    return {
        "provider": "Google",
        "model": "gemini-3-pro-preview",
        "response": response.text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_sec": round(duration, 2),
        # Gemini 3 Pro: Preise noch nicht final, schätze $2.50/1M input, $10/1M output
        "cost_usd": round((input_tokens * 2.50 + output_tokens * 10) / 1_000_000, 4)
    }


def parse_claims(response_text):
    """Versucht Claims aus der Response zu extrahieren."""
    try:
        # Versuche JSON zu finden
        import re
        json_match = re.search(r'\{[\s\S]*"claims"[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            return data.get("claims", [])
    except:
        pass
    return []


def analyze_claims(claims):
    """Analysiert die Qualität der Claims."""
    if not claims:
        return {"count": 0, "types": {}, "evidence_classes": {}}
    
    types = {}
    evidence_classes = {}
    
    for claim in claims:
        t = claim.get("type", "UNKNOWN")
        types[t] = types.get(t, 0) + 1
        
        ec = claim.get("evidence_class", "?")
        evidence_classes[ec] = evidence_classes.get(ec, 0) + 1
    
    return {
        "count": len(claims),
        "types": types,
        "evidence_classes": evidence_classes
    }


def run_comparison():
    """Führt den Vergleichstest durch."""
    
    print("\n" + "=" * 60)
    print("GEMINI vs CLAUDE VERGLEICHSTEST")
    print("=" * 60)
    print(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Thema: {TEST_TOPIC}")
    
    # 1. API Test
    api_status = test_api_connection()
    
    if not any(api_status.values()):
        print("\n❌ Keine API funktioniert! Abbruch.")
        return
    
    results = []
    
    # 2. Claim Mining Tests
    print("\n" + "=" * 60)
    print("2. CLAIM MINING VERGLEICH")
    print("=" * 60)
    
    # Claude
    if api_status.get("claude"):
        model_name = api_status.get("claude_model", "claude-3-5-sonnet-20241022")
        print(f"\n🧪 Teste {model_name}...")
        try:
            result = test_claim_mining_claude(model_name)
            claims = parse_claims(result["response"])
            result["claims_analysis"] = analyze_claims(claims)
            results.append(result)
            print(f"   ✅ {result['claims_analysis']['count']} Claims in {result['duration_sec']}s")
            print(f"   💰 Kosten: ${result['cost_usd']}")
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
    
    # Gemini Flash (Budget)
    if api_status.get("gemini_flash"):
        print("\n🧪 Teste Gemini 2.5 Flash (Budget)...")
        try:
            result = test_claim_mining_gemini_flash()
            claims = parse_claims(result["response"])
            result["claims_analysis"] = analyze_claims(claims)
            results.append(result)
            print(f"   ✅ {result['claims_analysis']['count']} Claims in {result['duration_sec']}s")
            print(f"   💰 Kosten: ${result['cost_usd']}")
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
    
    # Gemini 3 Pro (Premium)
    if api_status.get("gemini_pro"):
        print("\n🧪 Teste Gemini 3 Pro (Premium)...")
        try:
            result = test_claim_mining_gemini_pro()
            claims = parse_claims(result["response"])
            result["claims_analysis"] = analyze_claims(claims)
            results.append(result)
            print(f"   ✅ {result['claims_analysis']['count']} Claims in {result['duration_sec']}s")
            print(f"   💰 Kosten: ${result['cost_usd']}")
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
    
    # 3. Ergebnisvergleich
    print("\n" + "=" * 60)
    print("3. ERGEBNISVERGLEICH")
    print("=" * 60)
    
    print("\n┌────────────────────────────┬─────────┬──────────┬──────────┬───────────┐")
    print("│ Modell                     │ Claims  │ Zeit (s) │ Tokens   │ Kosten    │")
    print("├────────────────────────────┼─────────┼──────────┼──────────┼───────────┤")
    for r in results:
        model_short = r["model"][:26]
        claims = r["claims_analysis"]["count"]
        tokens = r["input_tokens"] + r["output_tokens"]
        print(f"│ {model_short:<26} │ {claims:>7} │ {r['duration_sec']:>8.2f} │ {tokens:>8} │ ${r['cost_usd']:<8} │")
    print("└────────────────────────────┴─────────┴──────────┴──────────┴───────────┘")
    
    # Evidence Class Verteilung
    print("\n📊 Evidence Class Verteilung:")
    for r in results:
        ec = r["claims_analysis"]["evidence_classes"]
        print(f"   {r['model'][:25]}: A={ec.get('A',0)}, B={ec.get('B',0)}, C={ec.get('C',0)}")
    
    # 4. Qualitative Ausgabe
    print("\n" + "=" * 60)
    print("4. BEISPIEL-CLAIMS (erste 3 pro Modell)")
    print("=" * 60)
    
    for r in results:
        print(f"\n--- {r['model']} ---")
        claims = parse_claims(r["response"])[:3]
        for c in claims:
            print(f"  [{c.get('evidence_class','?')}] {c.get('statement','')[:80]}...")
    
    # 5. Speichern
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"tests/results/gemini_comparison_{timestamp}.json"
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "topic": TEST_TOPIC,
        "api_status": api_status,
        "results": results
    }
    
    os.makedirs("tests/results", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Vollständige Ergebnisse: {output_file}")
    
    # 6. Fazit
    print("\n" + "=" * 60)
    print("FAZIT")
    print("=" * 60)
    if len(results) >= 2:
        sorted_by_claims = sorted(results, key=lambda x: x["claims_analysis"]["count"], reverse=True)
        sorted_by_cost = sorted(results, key=lambda x: x["cost_usd"])
        sorted_by_speed = sorted(results, key=lambda x: x["duration_sec"])
        
        print(f"📈 Meiste Claims:    {sorted_by_claims[0]['model']}")
        print(f"💰 Günstigstes:      {sorted_by_cost[0]['model']} (${sorted_by_cost[0]['cost_usd']})")
        print(f"⚡ Schnellstes:      {sorted_by_speed[0]['model']} ({sorted_by_speed[0]['duration_sec']}s)")


if __name__ == "__main__":
    run_comparison()
