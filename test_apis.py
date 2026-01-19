import os
from dotenv import load_dotenv

load_dotenv()

# Test 1: Anthropic - Welche Claude Modelle?
print("=" * 50)
print("🔵 ANTHROPIC API TEST")
print("=" * 50)
try:
    import anthropic
    client = anthropic.Anthropic()
    
    # Test Claude 4 Sonnet
    models_to_test = [
        "claude-4-sonnet-20260101",
        "claude-4-opus-20260101", 
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
    ]
    
    for model in models_to_test:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print(f"✅ {model} - VERFÜGBAR")
        except Exception as e:
            if "not_found" in str(e).lower() or "invalid" in str(e).lower():
                print(f"❌ {model} - Nicht gefunden")
            else:
                print(f"⚠️ {model} - Fehler: {str(e)[:50]}")
except Exception as e:
    print(f"❌ Anthropic Fehler: {e}")

# Test 2: OpenAI - Welche GPT Modelle?
print("\n" + "=" * 50)
print("🟢 OPENAI API TEST")
print("=" * 50)
try:
    import openai
    client = openai.OpenAI()
    
    models_to_test = [
        "gpt-5.1",
        "gpt-5.1-instant",
        "gpt-5",
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o1-mini",
    ]
    
    for model in models_to_test:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print(f"✅ {model} - VERFÜGBAR")
        except Exception as e:
            if "not exist" in str(e).lower() or "invalid" in str(e).lower():
                print(f"❌ {model} - Nicht gefunden")
            else:
                print(f"⚠️ {model} - Fehler: {str(e)[:80]}")
except Exception as e:
    print(f"❌ OpenAI Fehler: {e}")

# Test 3: Gemini
print("\n" + "=" * 50)
print("🟡 GEMINI API TEST")
print("=" * 50)
try:
    import google.generativeai as genai
    
    # Gemini Key aus Umgebungsvariable
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Liste verfügbare Modelle
    print("Verfügbare Gemini Modelle:")
    for model in genai.list_models():
        if "generateContent" in [m.name for m in model.supported_generation_methods]:
            print(f"  ✅ {model.name}")
except Exception as e:
    print(f"❌ Gemini Fehler: {e}")
