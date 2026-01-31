"""
HayMAS - Konfiguration für LLMs und System-Einstellungen

Unterstützt Premium und Budget Modell-Varianten pro Agent.
"""

import os
import json
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Dict, Literal

# Lade Umgebungsvariablen aus .env
load_dotenv()

# =============================================================================
# API Keys
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# =============================================================================
# Modell-Definitionen
# =============================================================================

@dataclass
class ModelConfig:
    """Konfiguration für ein einzelnes Modell."""
    name: str
    provider: Literal["anthropic", "openai", "gemini"]
    description: str
    cost_tier: Literal["premium", "budget"]

# Verfügbare Modelle nach Anbieter
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    # Anthropic Claude
    "claude-opus-4-5": ModelConfig(
        name="claude-opus-4-5",
        provider="anthropic",
        description="Claude Opus 4.5 - Stärkstes Reasoning",
        cost_tier="premium"
    ),
    "claude-sonnet-4-5": ModelConfig(
        name="claude-sonnet-4-5",
        provider="anthropic",
        description="Claude Sonnet 4.5 - Beste Balance",
        cost_tier="premium"
    ),
    "claude-haiku-4-5": ModelConfig(
        name="claude-haiku-4-5-20251001",
        provider="anthropic",
        description="Claude Haiku 4.5 - Schnell & günstig",
        cost_tier="budget"
    ),
    
    # OpenAI GPT
    "gpt-5.2": ModelConfig(
        name="gpt-5.2",
        provider="openai",
        description="GPT-5.2 - Neuestes OpenAI Modell",
        cost_tier="premium"
    ),
    "gpt-5.1": ModelConfig(
        name="gpt-5.1",
        provider="openai",
        description="GPT-5.1 - Sehr gute Textqualität",
        cost_tier="premium"
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        provider="openai",
        description="GPT-4o - Bewährt & zuverlässig",
        cost_tier="budget"
    ),
    "o3-mini": ModelConfig(
        name="o3-mini",
        provider="openai",
        description="o3-mini - Reasoning-Spezialist",
        cost_tier="premium"
    ),
    
    # Google Gemini
    "gemini-deep-research": ModelConfig(
        name="deep-research-pro-preview-12-2025",
        provider="gemini",
        description="Gemini Deep Research - Für Recherche optimiert",
        cost_tier="premium"
    ),
    "gemini-3-pro": ModelConfig(
        name="gemini-3-pro-preview",
        provider="gemini",
        description="Gemini 3 Pro - Neuestes Google Modell",
        cost_tier="premium"
    ),
    "gemini-2.5-flash": ModelConfig(
        name="gemini-2.5-flash",
        provider="gemini",
        description="Gemini 2.5 Flash - Schnell & günstig",
        cost_tier="budget"
    ),
}

# =============================================================================
# Agenten-Konfiguration (Premium vs Budget)
# =============================================================================

@dataclass
class AgentModelConfig:
    """Premium und Budget Modell für einen Agenten."""
    premium: str  # Key aus AVAILABLE_MODELS
    budget: str   # Key aus AVAILABLE_MODELS
    description: str

# Modell-Zuordnung pro Agent
AGENT_MODELS: Dict[str, AgentModelConfig] = {
    "orchestrator": AgentModelConfig(
        premium="claude-opus-4-5",
        budget="claude-sonnet-4-5",
        description="Plant Recherche-Strategie und koordiniert Agenten"
    ),
    "researcher": AgentModelConfig(
        premium="claude-sonnet-4-5",  # Gemini hat oft Quota-Probleme
        budget="gpt-4o",
        description="Führt Web-Recherche in 3 Runden durch"
    ),
    "writer": AgentModelConfig(
        premium="gpt-5.2",
        budget="gpt-5.1",
        description="Schreibt den Wissensartikel"
    ),
    "editor": AgentModelConfig(
        premium="claude-sonnet-4-5",
        budget="claude-haiku-4-5",
        description="Prüft Qualität und gibt Feedback"
    ),
    # NEU: Gemini-basierter Verifier für Multi-LLM Verification
    "verifier": AgentModelConfig(
        premium="gemini-3-pro",
        budget="gemini-2.5-flash",
        description="Cross-LLM Verification mit Gemini"
    ),
}

def get_model_for_agent(agent_name: str, tier: Literal["premium", "budget"] = "premium") -> ModelConfig:
    """
    Gibt die Modell-Konfiguration für einen Agenten zurück.
    
    Args:
        agent_name: Name des Agenten (orchestrator, researcher, writer, editor)
        tier: "premium" oder "budget"
    
    Returns:
        ModelConfig mit Modellname und Provider
    """
    if agent_name not in AGENT_MODELS:
        raise ValueError(f"Unbekannter Agent: {agent_name}")
    
    agent_config = AGENT_MODELS[agent_name]
    model_key = agent_config.premium if tier == "premium" else agent_config.budget
    
    if model_key not in AVAILABLE_MODELS:
        raise ValueError(f"Unbekanntes Modell: {model_key}")
    
    return AVAILABLE_MODELS[model_key]

# =============================================================================
# System-Einstellungen
# =============================================================================

# Maximale Anzahl Tool-Aufrufe pro Agent-Durchlauf
MAX_TOOL_CALLS = 15

# Maximale Zeichen für Tool-Ergebnisse (verhindert Token-Explosion)
# ~2500 Zeichen ≈ ~625 Tokens
MAX_TOOL_RESULT_CHARS = 2500

# Maximale Zeichen pro einzelner Quelle (für strukturierte Ergebnisse)
# Stellt sicher, dass alle Quellen erhalten bleiben statt Gesamt-Truncation
MAX_CHARS_PER_SOURCE = 400

# Maximale Anzahl Iterationen für QS-Schleifen (Editor-Feedback)
MAX_EDITOR_ITERATIONS = 2

# Output-Verzeichnis für generierte Dateien
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Sprache für Wissensartikel
DEFAULT_LANGUAGE = "de"

# =============================================================================
# Wissensartikel-Einstellungen
# =============================================================================

# Ziel-Umfang für Artikel
ARTICLE_TARGET_SECTIONS = 7  # Ca. 7 Hauptabschnitte
ARTICLE_MIN_WORDS = 2000     # Mindestens 2000 Wörter

# Recherche-Einstellungen
RESEARCH_ROUNDS = 3  # Anzahl Recherche-Runden (Grundlagen, Aktuelles, Deep-Dive)
SEARCH_RESULTS_PER_ROUND = 5  # Ergebnisse pro Suchanfrage

# =============================================================================
# Logging
# =============================================================================

# Log-Level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Live-Updates in der UI aktivieren
ENABLE_LIVE_UPDATES = True

# =============================================================================
# Hilfsfunktionen
# =============================================================================

def get_api_key(provider: str) -> str:
    """Gibt den API-Key für einen Provider zurück."""
    keys = {
        "anthropic": ANTHROPIC_API_KEY,
        "openai": OPENAI_API_KEY,
        "gemini": GEMINI_API_KEY,
        "tavily": TAVILY_API_KEY,
    }
    return keys.get(provider, "")

def validate_api_keys() -> Dict[str, bool]:
    """Prüft welche API-Keys gesetzt sind."""
    return {
        "anthropic": bool(ANTHROPIC_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "tavily": bool(TAVILY_API_KEY),
    }

# =============================================================================
# API Key Management (für Docker/Frontend)
# =============================================================================

# Pfad zur persistenten Config-Datei (im Container: /app/data/config.json)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "config.json")

def _load_config() -> Dict:
    """Lädt die persistente Konfiguration."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_config(config: Dict):
    """Speichert die persistente Konfiguration."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def reload_api_keys():
    """
    Lädt API-Keys neu - priorisiert config.json über .env.
    Wird beim Server-Start und nach Änderungen aufgerufen.
    """
    global ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY
    
    # Zuerst aus .env laden (Fallback)
    load_dotenv(override=True)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    
    # Dann aus config.json überschreiben (falls vorhanden)
    config = _load_config()
    api_keys = config.get("api_keys", {})
    
    if api_keys.get("anthropic"):
        ANTHROPIC_API_KEY = api_keys["anthropic"]
    if api_keys.get("openai"):
        OPENAI_API_KEY = api_keys["openai"]
    if api_keys.get("gemini"):
        GEMINI_API_KEY = api_keys["gemini"]
    if api_keys.get("tavily"):
        TAVILY_API_KEY = api_keys["tavily"]

def save_api_keys(keys: Dict[str, str]):
    """
    Speichert API-Keys in der persistenten Konfiguration.
    Leere Strings werden ignoriert (behalten vorherigen Wert).
    """
    config = _load_config()
    existing_keys = config.get("api_keys", {})
    
    # Nur nicht-leere Keys überschreiben
    for provider, key in keys.items():
        if key:  # Nur wenn nicht leer
            existing_keys[provider] = key
    
    config["api_keys"] = existing_keys
    _save_config(config)
    
    # Keys neu laden
    reload_api_keys()

def get_api_keys_masked() -> Dict[str, str]:
    """
    Gibt maskierte API-Keys zurück für die UI.
    Zeigt nur die ersten 8 und letzten 4 Zeichen.
    """
    def mask(key: str) -> str:
        if not key:
            return ""
        if len(key) <= 16:
            return "•" * len(key)
        return f"{key[:8]}{'•' * (len(key) - 12)}{key[-4:]}"
    
    return {
        "anthropic": mask(ANTHROPIC_API_KEY),
        "openai": mask(OPENAI_API_KEY),
        "gemini": mask(GEMINI_API_KEY),
        "tavily": mask(TAVILY_API_KEY),
    }

# Initial laden beim Import
reload_api_keys()
