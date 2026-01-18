import os
from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()

print("=" * 60)
print("🔵 ANTHROPIC - Test mit KORREKTEN Modellnamen")
print("=" * 60)

# Neue Modellnamen laut Dokumentation
models_to_test = [
    "claude-sonnet-4-5",      # Claude Sonnet 4.5
    "claude-opus-4-5",        # Claude Opus 4.5
    "claude-sonnet-4",        # Claude Sonnet 4
    "claude-opus-4",          # Claude Opus 4
    "claude-opus-4-1",        # Claude Opus 4.1
    "claude-haiku-4",         # Claude Haiku 4.x
    "claude-haiku-3",         # Claude Haiku 3
]

for model in models_to_test:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}]
        )
        print(f"✅ {model} - VERFÜGBAR")
    except anthropic.NotFoundError:
        print(f"❌ {model} - Nicht gefunden")
    except anthropic.AuthenticationError as e:
        print(f"🔑 {model} - Auth-Fehler")
    except Exception as e:
        print(f"⚠️ {model} - {type(e).__name__}: {str(e)[:60]}")

# Auch Models API testen
print("\n" + "=" * 60)
print("📋 Verfügbare Modelle via Models API:")
print("=" * 60)
try:
    models = client.models.list()
    for m in models.data:
        print(f"  ✅ {m.id}")
except Exception as e:
    print(f"❌ Models API Fehler: {e}")
