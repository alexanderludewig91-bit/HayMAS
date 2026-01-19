import os
from dotenv import load_dotenv
load_dotenv()

# Test 1: Anthropic - genauerer Test
print("=" * 60)
print("🔵 ANTHROPIC API TEST (detailliert)")
print("=" * 60)
try:
    import anthropic
    client = anthropic.Anthropic()
    
    models_to_test = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest", 
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
    
    for model in models_to_test:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            print(f"✅ {model}")
        except anthropic.NotFoundError:
            print(f"❌ {model} - Nicht gefunden")
        except anthropic.AuthenticationError as e:
            print(f"🔑 {model} - Auth-Fehler: API Key ungültig?")
        except Exception as e:
            print(f"⚠️ {model} - {type(e).__name__}: {str(e)[:60]}")
except Exception as e:
    print(f"❌ Anthropic Import-Fehler: {e}")

# Test 2: OpenAI - erweitert
print("\n" + "=" * 60)
print("🟢 OPENAI API TEST (detailliert)")
print("=" * 60)
try:
    import openai
    client = openai.OpenAI()
    
    # Liste alle verfügbaren Modelle
    print("Verfügbare Chat-Modelle:")
    models = client.models.list()
    chat_models = [m.id for m in models if 'gpt' in m.id.lower() or 'o1' in m.id.lower() or 'o3' in m.id.lower()]
    for m in sorted(chat_models):
        print(f"  ✅ {m}")
except Exception as e:
    print(f"❌ OpenAI Fehler: {e}")

# Test 3: Gemini
print("\n" + "=" * 60)
print("🟡 GEMINI API TEST")
print("=" * 60)
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    print("Verfügbare Gemini Modelle für Content-Generierung:")
    for model in genai.list_models():
        if "generateContent" in [m for m in model.supported_generation_methods]:
            print(f"  ✅ {model.name}")
except Exception as e:
    print(f"❌ Gemini Fehler: {e}")
